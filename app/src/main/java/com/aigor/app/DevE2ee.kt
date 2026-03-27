package com.aigor.app

import android.util.Base64
import org.json.JSONObject
import java.security.KeyFactory
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.PublicKey
import java.security.SecureRandom
import java.security.Security
import org.bouncycastle.asn1.x509.SubjectPublicKeyInfo
import org.bouncycastle.crypto.params.Ed25519PublicKeyParameters
import org.bouncycastle.crypto.signers.Ed25519Signer
import org.bouncycastle.jce.provider.BouncyCastleProvider
import java.security.spec.X509EncodedKeySpec
import javax.crypto.Cipher
import javax.crypto.KeyAgreement
import javax.crypto.Mac
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

object DevE2ee {
    init {
        if (Security.getProvider("BC") == null) {
            Security.addProvider(BouncyCastleProvider())
        }
    }
    data class EncryptResult(
        val envelope: JSONObject,
        val responseKey: ByteArray,
    )

    data class CanonicalRatchetState(
        val rootKey: ByteArray,
        val sendChainKey: ByteArray,
        val recvChainKey: ByteArray,
        val ratchetStep: Int,
        val lastPeerRatchetPubB64: String? = null,
    ) {
        fun messageKey(counter: Int, label: String, direction: Direction): ByteArray {
            val chainKey = if (direction == Direction.SEND) sendChainKey else recvChainKey
            return deriveMessageKey(chainKey, counter, label)
        }
    }

    enum class Direction { SEND, RECV }

    fun encryptForBridge(plaintext: String, bridgePublicKeyB64: String, ad: String, otkPublicKeyB64: String? = null, otkId: String? = null, counter: Int = 0): EncryptResult {
        val kpg = KeyPairGenerator.getInstance("X25519")
        val eph = kpg.generateKeyPair()

        val bridgePub = decodePublicKey(bridgePublicKeyB64)
        val ka = KeyAgreement.getInstance("X25519")
        ka.init(eph.private)
        ka.doPhase(bridgePub, true)
        var shared = ka.generateSecret()

        if (!otkPublicKeyB64.isNullOrBlank()) {
            val otkPub = decodePublicKey(otkPublicKeyB64)
            val kaOtk = KeyAgreement.getInstance("X25519")
            kaOtk.init(eph.private)
            kaOtk.doPhase(otkPub, true)
            shared += kaOtk.generateSecret()
        }

        val salt = ByteArray(16).also { SecureRandom().nextBytes(it) }
        var baseKey = hkdfSha256(shared, salt, "aigor-e2ee-v1", 32)

        val ratchet = kpg.generateKeyPair()
        val kaRatchet = KeyAgreement.getInstance("X25519")
        kaRatchet.init(ratchet.private)
        kaRatchet.doPhase(bridgePub, true)
        val ratchetShared = kaRatchet.generateSecret()
        val ratchetPubBytes = ratchet.public.encoded
        val ratchetSalt = MessageDigest.getInstance("SHA-256").digest(ratchetPubBytes).copyOfRange(0, 16)
        baseKey = hkdfSha256(baseKey + ratchetShared, ratchetSalt, "aigor-ratchet-step-v1", 32)

        val state = canonicalStateFromRoot(
            rootKey = baseKey,
            ratchetStep = 1,
            lastPeerRatchetPubB64 = Base64.encodeToString(bridgePub.encoded, Base64.NO_WRAP),
        )
        val key = state.messageKey(counter, "c2s", Direction.SEND)
        val iv = ByteArray(12).also { SecureRandom().nextBytes(it) }

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, iv))
        cipher.updateAAD(ad.toByteArray(Charsets.UTF_8))
        val ct = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))

        val env = JSONObject().apply {
            put("v", 1)
            put("alg", "x25519-aesgcm-v1")
            put("headerId", "h-${Base64.encodeToString(MessageDigest.getInstance("SHA-256").digest(ratchetPubBytes), Base64.NO_WRAP).take(10)}")
            put("ephemeralPub", Base64.encodeToString(eph.public.encoded, Base64.NO_WRAP))
            put("ratchetPub", Base64.encodeToString(ratchetPubBytes, Base64.NO_WRAP))
            put("salt", Base64.encodeToString(salt, Base64.NO_WRAP))
            put("iv", Base64.encodeToString(iv, Base64.NO_WRAP))
            put("ciphertext", Base64.encodeToString(ct, Base64.NO_WRAP))
            put("ad", ad)
            put("counter", counter)
            put("ratchetStep", state.ratchetStep)
            put("keyModel", "canonical-v1")
            if (!otkId.isNullOrBlank()) put("otkId", otkId)
            put("expectEncryptedReply", true)
        }

        return EncryptResult(env, baseKey)
    }

    fun decryptWithKey(baseKey: ByteArray, env: JSONObject): String {
        val ad = env.optString("ad", "")
        val iv = Base64.decode(env.optString("iv", ""), Base64.DEFAULT)
        val ct = Base64.decode(env.optString("ciphertext", ""), Base64.DEFAULT)
        val counter = env.optInt("counter", 0)
        val ratchetStep = env.optInt("ratchetStep", 1)
        val state = canonicalStateFromRoot(
            rootKey = baseKey,
            ratchetStep = ratchetStep,
            lastPeerRatchetPubB64 = env.optString("ratchetPub", "").ifBlank { null },
        )
        val key = state.messageKey(counter, "s2c", Direction.SEND)

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, iv))
        cipher.updateAAD(ad.toByteArray(Charsets.UTF_8))
        val pt = cipher.doFinal(ct)
        return String(pt, Charsets.UTF_8)
    }

    fun encryptAttachment(base64Data: String, baseKey: ByteArray, name: String, mime: String, ad: String, counter: Int): JSONObject {
        val raw = Base64.decode(base64Data, Base64.DEFAULT)
        val state = canonicalStateFromRoot(rootKey = baseKey, ratchetStep = 1)
        val key = state.messageKey(counter, "att", Direction.SEND)
        val iv = ByteArray(12).also { SecureRandom().nextBytes(it) }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, iv))
        cipher.updateAAD(ad.toByteArray(Charsets.UTF_8))
        val ct = cipher.doFinal(raw)
        return JSONObject().apply {
            put("name", name)
            put("mime", mime)
            put("alg", "aes-gcm-v1")
            put("iv", Base64.encodeToString(iv, Base64.NO_WRAP))
            put("ciphertext", Base64.encodeToString(ct, Base64.NO_WRAP))
            put("ad", ad)
            put("counter", counter)
        }
    }

    fun verifySignedPreKey(identitySignPubB64: String, signedPreKeyPubB64: String, sigB64: String): Boolean {
        return try {
            val pubBytes = Base64.decode(identitySignPubB64, Base64.DEFAULT)
            val spkBytes = Base64.decode(signedPreKeyPubB64, Base64.DEFAULT)
            val sigBytes = Base64.decode(sigB64, Base64.DEFAULT)

            val spki = SubjectPublicKeyInfo.getInstance(pubBytes)
            val rawPub = spki.publicKeyData.bytes
            val pub = Ed25519PublicKeyParameters(rawPub, 0)
            val verifier = Ed25519Signer()
            verifier.init(false, pub)
            verifier.update(spkBytes, 0, spkBytes.size)
            verifier.verifySignature(sigBytes)
        } catch (_: Exception) {
            false
        }
    }

    private fun sha256Hex(bytes: ByteArray): String {
        return MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
    }

    private fun decodePublicKey(b64: String): PublicKey {
        val bytes = Base64.decode(b64, Base64.DEFAULT)
        val kf = KeyFactory.getInstance("X25519")
        return kf.generatePublic(X509EncodedKeySpec(bytes))
    }

    private fun canonicalStateFromRoot(
        rootKey: ByteArray,
        ratchetStep: Int,
        lastPeerRatchetPubB64: String? = null,
    ): CanonicalRatchetState {
        val sendChainKey = deriveChainKey(rootKey, "send", ratchetStep)
        val recvChainKey = deriveChainKey(rootKey, "recv", ratchetStep)
        return CanonicalRatchetState(
            rootKey = rootKey,
            sendChainKey = sendChainKey,
            recvChainKey = recvChainKey,
            ratchetStep = ratchetStep,
            lastPeerRatchetPubB64 = lastPeerRatchetPubB64,
        )
    }

    private fun deriveChainKey(rootKey: ByteArray, direction: String, ratchetStep: Int): ByteArray {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(rootKey, "HmacSHA256"))
        val d = mac.doFinal("chain:$direction:step:$ratchetStep".toByteArray(Charsets.UTF_8))
        return d.copyOfRange(0, 32)
    }

    private fun deriveMessageKey(chainKey: ByteArray, counter: Int, label: String): ByteArray {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(chainKey, "HmacSHA256"))
        val d = mac.doFinal("$label:$counter".toByteArray(Charsets.UTF_8))
        return d.copyOfRange(0, 32)
    }

    private fun hkdfSha256(ikm: ByteArray, salt: ByteArray, info: String, len: Int): ByteArray {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(salt, "HmacSHA256"))
        val prk = mac.doFinal(ikm)

        var t = ByteArray(0)
        val okm = ByteArray(len)
        var offset = 0
        var counter = 1

        while (offset < len) {
            mac.init(SecretKeySpec(prk, "HmacSHA256"))
            mac.update(t)
            mac.update(info.toByteArray(Charsets.UTF_8))
            mac.update(counter.toByte())
            t = mac.doFinal()
            val c = minOf(t.size, len - offset)
            System.arraycopy(t, 0, okm, offset, c)
            offset += c
            counter++
        }

        return okm
    }
}
