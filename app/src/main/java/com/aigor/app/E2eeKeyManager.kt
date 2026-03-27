package com.aigor.app

import android.content.Context
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.SecureRandom
import java.security.Signature
import java.security.spec.PKCS8EncodedKeySpec
import java.security.spec.X509EncodedKeySpec
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

class E2eeKeyManager(private val context: Context) {
    private val prefs = context.getSharedPreferences("aigor_app_e2ee", Context.MODE_PRIVATE)

    data class LocalBundle(
        val deviceId: String,
        val identityKey: String,
        val signedPreKey: String,
        val signedPreKeySignature: String,
        val oneTimePreKeys: List<String>,
    )

    fun ensureLocalBundle(): LocalBundle {
        val deviceId = ensureDeviceId()

        val identityRef = prefs.getString("identity_sign_key_ref", null)
            ?: "identity-ed25519-v1".also { prefs.edit().putString("identity_sign_key_ref", it).apply() }
        val identityPair = ensureEd25519KeyPair(identityRef)
        val identityPubB64 = b64(identityPair.public.encoded)

        val signedPreKeyRef = prefs.getString("signed_prekey_ref", null)
            ?.let { if (it == "signed-prekey-p256-v1") "signed-prekey-x25519-v1" else it }
            ?: "signed-prekey-x25519-v1"
        if (prefs.getString("signed_prekey_ref", null) != signedPreKeyRef) {
            prefs.edit().putString("signed_prekey_ref", signedPreKeyRef).apply()
        }
        val signedPreKey = ensureSignedPreKey(identityPair, signedPreKeyRef)

        val otkPool = ensureOtkPool(minSize = 10)
        val otkPubs = otkPool
            .filter { it.optString("consumed_at", "").isBlank() }
            .mapNotNull { it.optString("pub_b64", "").ifBlank { null } }

        return LocalBundle(
            deviceId = deviceId,
            identityKey = identityPubB64,
            signedPreKey = signedPreKey.publicKeyB64,
            signedPreKeySignature = signedPreKey.signatureB64,
            oneTimePreKeys = otkPubs,
        )
    }

    private data class SignedPreKeyMaterial(
        val publicKeyB64: String,
        val signatureB64: String,
    )

    private fun ensureDeviceId(): String {
        return prefs.getString("device_id", null)
            ?: randomB64(16).also { prefs.edit().putString("device_id", it).apply() }
    }

    private fun ensureSignedPreKey(identity: KeyPair, ref: String): SignedPreKeyMaterial {
        val now = System.currentTimeMillis()
        val rotateEveryMs = 30L * 24L * 60L * 60L * 1000L

        val existingMeta = parseJsonObject(prefs.getString("signed_prekey_meta", null))
        val needsRotation = existingMeta == null || now >= existingMeta.optLong("expires_at", 0L)

        if (needsRotation) {
            val pair = generateX25519()
            val spkPubB64 = b64(pair.public.encoded)
            val sigB64 = signEd25519(identity.private.encoded, Base64.decode(spkPubB64, Base64.DEFAULT))

            storeKeyPair(ref, pair.private.encoded, pair.public.encoded)

            val spkId = "spk-${UUID.randomUUID()}"
            val createdAt = now
            val expiresAt = now + rotateEveryMs
            val meta = JSONObject().apply {
                put("spk_id", spkId)
                put("created_at", createdAt)
                put("expires_at", expiresAt)
                put("last_rotated_at", createdAt)
            }

            prefs.edit()
                .putString("signed_prekey_signature_b64", sigB64)
                .putString("signed_prekey_meta", meta.toString())
                .putString("signed_prekey", spkPubB64)
                .putString("signed_prekey_sig", sigB64)
                .apply()

            return SignedPreKeyMaterial(spkPubB64, sigB64)
        }

        val existing = loadKeyPair(ref, "X25519")
        if (existing != null) {
            val pubB64 = b64(existing.public.encoded)
            val sigB64 = prefs.getString("signed_prekey_signature_b64", null)
                ?: signEd25519(identity.private.encoded, existing.public.encoded).also {
                    prefs.edit().putString("signed_prekey_signature_b64", it).apply()
                }

            if (prefs.getString("signed_prekey", null).isNullOrBlank() || prefs.getString("signed_prekey_sig", null).isNullOrBlank()) {
                prefs.edit().putString("signed_prekey", pubB64).putString("signed_prekey_sig", sigB64).apply()
            }
            return SignedPreKeyMaterial(pubB64, sigB64)
        }

        // Fallback coherent: if metadata existed but key material disappeared, regenerate.
        val regenerated = generateX25519()
        storeKeyPair(ref, regenerated.private.encoded, regenerated.public.encoded)
        val regeneratedPub = b64(regenerated.public.encoded)
        val regeneratedSig = signEd25519(identity.private.encoded, regenerated.public.encoded)
        prefs.edit()
            .putString("signed_prekey_signature_b64", regeneratedSig)
            .putString("signed_prekey", regeneratedPub)
            .putString("signed_prekey_sig", regeneratedSig)
            .apply()
        return SignedPreKeyMaterial(regeneratedPub, regeneratedSig)
    }

    private fun ensureOtkPool(minSize: Int): List<JSONObject> {
        val now = System.currentTimeMillis()
        val raw = prefs.getString("otk_pool", null)
        val existing = parseOtkPool(raw).toMutableList()

        val activeCount = existing.count { it.optString("consumed_at", "").isBlank() }
        val needed = (minSize - activeCount).coerceAtLeast(0)
        if (needed > 0) {
            repeat(needed) {
                val pair = generateX25519()
                val id = "otk-${UUID.randomUUID()}"
                storeKeyPair("otk:$id", pair.private.encoded, pair.public.encoded)
                existing += JSONObject().apply {
                    put("id", id)
                    put("pub_b64", b64(pair.public.encoded))
                    put("consumed_at", JSONObject.NULL)
                    put("batch_created_at", now)
                }
            }
            saveOtkPool(existing)
        }

        if (prefs.getString("otk_list", null).isNullOrBlank()) {
            val compat = existing
                .filter { it.optString("consumed_at", "").isBlank() }
                .mapNotNull { it.optString("pub_b64", "").ifBlank { null } }
            prefs.edit().putString("otk_list", JSONObject().put("keys", JSONArray(compat)).toString()).apply()
        }

        return existing
    }

    private fun saveOtkPool(items: List<JSONObject>) {
        val arr = JSONArray()
        items.forEach { arr.put(it) }
        prefs.edit().putString("otk_pool", arr.toString()).apply()
    }

    private fun parseOtkPool(raw: String?): List<JSONObject> {
        if (raw.isNullOrBlank()) return emptyList()
        return try {
            val arr = JSONArray(raw)
            List(arr.length()) { i -> arr.optJSONObject(i) ?: JSONObject() }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun parseJsonObject(raw: String?): JSONObject? {
        if (raw.isNullOrBlank()) return null
        return try {
            JSONObject(raw)
        } catch (_: Exception) {
            null
        }
    }

    private fun ensureEd25519KeyPair(ref: String): KeyPair {
        loadKeyPair(ref, "Ed25519")?.let { return it }
        val kpg = KeyPairGenerator.getInstance("Ed25519")
        val pair = kpg.generateKeyPair()
        storeKeyPair(ref, pair.private.encoded, pair.public.encoded)
        return pair
    }

    private fun generateX25519(): KeyPair {
        val kpg = KeyPairGenerator.getInstance("X25519")
        return kpg.generateKeyPair()
    }

    private fun signEd25519(privatePkcs8: ByteArray, payload: ByteArray): String {
        val kf = KeyFactory.getInstance("Ed25519")
        val priv = kf.generatePrivate(PKCS8EncodedKeySpec(privatePkcs8))
        val sig = Signature.getInstance("Ed25519")
        sig.initSign(priv)
        sig.update(payload)
        return b64(sig.sign())
    }

    private fun loadKeyPair(ref: String, algorithm: String): KeyPair? {
        val wrappedPriv = loadWrappedBlob("$ref.priv")
        val wrappedPub = loadWrappedBlob("$ref.pub")

        val privBytes: ByteArray
        val pubBytes: ByteArray

        if (wrappedPriv != null && wrappedPub != null) {
            privBytes = wrappedPriv
            pubBytes = wrappedPub
        } else {
            val legacy = loadLegacyJceksKeyPair(ref, algorithm) ?: return null
            // Lazy migration on first read.
            storeWrappedBlob("$ref.priv", legacy.private.encoded)
            storeWrappedBlob("$ref.pub", legacy.public.encoded)
            privBytes = legacy.private.encoded
            pubBytes = legacy.public.encoded
        }

        return try {
            val kf = KeyFactory.getInstance(algorithm)
            val priv = kf.generatePrivate(PKCS8EncodedKeySpec(privBytes))
            val pub = kf.generatePublic(X509EncodedKeySpec(pubBytes))
            KeyPair(pub, priv)
        } catch (_: Exception) {
            null
        }
    }

    private fun storeKeyPair(ref: String, privatePkcs8: ByteArray, publicX509: ByteArray) {
        storeWrappedBlob("$ref.priv", privatePkcs8)
        storeWrappedBlob("$ref.pub", publicX509)
    }

    private fun wrappedBlobKey(ref: String): String = "wrapped_blob:$ref"

    private fun storeWrappedBlob(ref: String, plaintext: ByteArray) {
        val key = getOrCreateWrappingKey()
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key)
        val iv = cipher.iv
        val encrypted = cipher.doFinal(plaintext)
        val serialized = "${b64(iv)}:${b64(encrypted)}"
        prefs.edit().putString(wrappedBlobKey(ref), serialized).apply()
    }

    private fun loadWrappedBlob(ref: String): ByteArray? {
        val serialized = prefs.getString(wrappedBlobKey(ref), null) ?: return null
        val parts = serialized.split(":")
        if (parts.size != 2) return null

        return try {
            val iv = Base64.decode(parts[0], Base64.DEFAULT)
            val ciphertext = Base64.decode(parts[1], Base64.DEFAULT)
            val key = getOrCreateWrappingKey()
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, iv))
            cipher.doFinal(ciphertext)
        } catch (_: Exception) {
            null
        }
    }

    @Synchronized
    private fun getOrCreateWrappingKey(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getKey(ANDROID_KEYSTORE_ALIAS, null) as? SecretKey)?.let { return it }

        val keyGen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        val baseBuilder = KeyGenParameterSpec.Builder(
            ANDROID_KEYSTORE_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
        )
            .setKeySize(256)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)

        val strongBoxAttempted = Build.VERSION.SDK_INT >= Build.VERSION_CODES.P
        if (strongBoxAttempted) {
            try {
                keyGen.init(baseBuilder.setIsStrongBoxBacked(true).build())
                return keyGen.generateKey()
            } catch (_: Exception) {
                // Fallback controlat a Android Keystore no-StrongBox.
            }
        }

        keyGen.init(baseBuilder.build())
        return keyGen.generateKey()
    }

    // Legacy read path només per migració lazy des de JCEKS + password en prefs.
    private fun loadLegacyJceksKeyPair(ref: String, algorithm: String): KeyPair? {
        val ks = loadLegacyOrCreateJceks()
        val prot = KeyStore.PasswordProtection(legacyKeyStorePassword())
        val privEntry = ks.getEntry("$ref.priv", prot) as? KeyStore.SecretKeyEntry ?: return null
        val pubEntry = ks.getEntry("$ref.pub", prot) as? KeyStore.SecretKeyEntry ?: return null
        return try {
            val kf = KeyFactory.getInstance(algorithm)
            val priv = kf.generatePrivate(PKCS8EncodedKeySpec(privEntry.secretKey.encoded))
            val pub = kf.generatePublic(X509EncodedKeySpec(pubEntry.secretKey.encoded))
            KeyPair(pub, priv)
        } catch (_: Exception) {
            null
        }
    }

    @Synchronized
    private fun loadLegacyOrCreateJceks(): KeyStore {
        val ks = KeyStore.getInstance("JCEKS")
        val file = legacyKeyStoreFile()
        val pass = legacyKeyStorePassword()
        if (file.exists()) {
            FileInputStream(file).use { ks.load(it, pass) }
        } else {
            ks.load(null, pass)
            persistLegacyKeyStore(ks)
        }
        return ks
    }

    private fun persistLegacyKeyStore(ks: KeyStore) {
        val file = legacyKeyStoreFile()
        val parent = file.parentFile
        if (parent != null && !parent.exists()) parent.mkdirs()
        FileOutputStream(file).use { ks.store(it, legacyKeyStorePassword()) }
    }

    private fun legacyKeyStoreFile(): File {
        return File(context.noBackupFilesDir, "e2ee_keys.jceks")
    }

    private fun legacyKeyStorePassword(): CharArray {
        val existing = prefs.getString("ks_pwd_b64", null)
        if (!existing.isNullOrBlank()) {
            return String(Base64.decode(existing, Base64.DEFAULT), Charsets.UTF_8).toCharArray()
        }
        // Legacy compat: only used if no previous password exists.
        val raw = ByteArray(24).also { SecureRandom().nextBytes(it) }
        val pwd = b64(raw)
        prefs.edit().putString("ks_pwd_b64", b64(pwd.toByteArray(Charsets.UTF_8))).apply()
        return pwd.toCharArray()
    }

    private fun randomB64(size: Int): String {
        val b = ByteArray(size)
        SecureRandom().nextBytes(b)
        return b64(b)
    }

    private fun b64(input: ByteArray): String = Base64.encodeToString(input, Base64.NO_WRAP)

    companion object {
        private const val ANDROID_KEYSTORE_ALIAS = "aigor_e2ee_wrapping_key_v1"
    }
}
