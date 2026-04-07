package ai.appenclaw.app

import android.content.Context
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
import java.util.concurrent.ConcurrentHashMap

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

    private data class SessionChainState(
        var rootKeySeed: ByteArray? = null,
        var sendChainSeed: ByteArray? = null,
        var recvChainSeed: ByteArray? = null,
        var sendChainCounter: Int = 0,
        var recvChainCounter: Int = 0,
    )

    private val ratchetStore = ConcurrentHashMap<String, SessionChainState>()
    private const val RATCHET_PREFS = "appenclaw_app_e2ee"
    private const val RATCHET_KEY_PREFIX = "ratchet_state::"
    @Volatile private var appContext: Context? = null

    fun configure(context: Context) {
        appContext = context.applicationContext
    }

    private fun fp(bytes: ByteArray): String = sha256Hex(bytes).take(12)

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
        var baseKey = hkdfSha256(shared, salt, "appenclaw-e2ee-v1", 32)

        val ratchet = kpg.generateKeyPair()
        val kaRatchet = KeyAgreement.getInstance("X25519")
        kaRatchet.init(ratchet.private)
        kaRatchet.doPhase(bridgePub, true)
        val ratchetShared = kaRatchet.generateSecret()
        val ratchetPubBytes = ratchet.public.encoded
        val ratchetSalt = MessageDigest.getInstance("SHA-256").digest(ratchetPubBytes).copyOfRange(0, 16)
        baseKey = hkdfSha256(baseKey + ratchetShared, ratchetSalt, "appenclaw-ratchet-step-v1", 32)

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
        val sessionIdField = env.optString("sessionId", "")
        val iv = Base64.decode(env.optString("iv", ""), Base64.DEFAULT)
        val ct = Base64.decode(env.optString("ciphertext", ""), Base64.DEFAULT)
        val counter = env.optInt("counter", 0)
        require(counter >= 1) { "Invalid s2c counter: $counter" }
        val sessionId = ad.ifBlank {
            sessionIdField.ifBlank {
                throw IllegalArgumentException("Missing session id (ad/sessionId) for s2c ratchet mix")
            }
        }

        val hasPersistentState = hasPersistentRatchetState(sessionId)
        val key = ratchetMixChainKey(sessionId, baseKey, "s2c", counter)
        val currentState = ratchetStore[sessionId]
        val hasRecvSeed = currentState?.recvChainSeed != null
        val recvCtr = currentState?.recvChainCounter ?: 0
        if (hasPersistentState && !hasRecvSeed && recvCtr == 0) {
            throw IllegalStateException("Persistent ratchet state exists but recv seed/counter are empty for sessionId=$sessionId")
        }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, iv))
        cipher.updateAAD(ad.toByteArray(Charsets.UTF_8))
        return cipher.doFinal(ct).toString(Charsets.UTF_8)
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

    private fun ratchetStateKey(sessionId: String): String = "$RATCHET_KEY_PREFIX$sessionId"

    private fun hasPersistentRatchetState(sessionId: String): Boolean {
        val prefs = appContext?.getSharedPreferences(RATCHET_PREFS, Context.MODE_PRIVATE) ?: return false
        return prefs.contains(ratchetStateKey(sessionId))
    }

    private fun loadPersistentRatchetState(sessionId: String): SessionChainState? {
        val prefs = appContext?.getSharedPreferences(RATCHET_PREFS, Context.MODE_PRIVATE) ?: return null
        val raw = prefs.getString(ratchetStateKey(sessionId), null) ?: return null
        return runCatching {
            val obj = JSONObject(raw)
            SessionChainState(
                rootKeySeed = obj.optString("rootKeySeed", "").takeIf { it.isNotBlank() }?.let { Base64.decode(it, Base64.DEFAULT) },
                sendChainSeed = obj.optString("sendChainSeed", "").takeIf { it.isNotBlank() }?.let { Base64.decode(it, Base64.DEFAULT) },
                recvChainSeed = obj.optString("recvChainSeed", "").takeIf { it.isNotBlank() }?.let { Base64.decode(it, Base64.DEFAULT) },
                sendChainCounter = obj.optInt("sendChainCounter", 0).coerceAtLeast(0),
                recvChainCounter = obj.optInt("recvChainCounter", 0).coerceAtLeast(0),
            )
        }.getOrElse {
            null
        }
    }

    private fun persistRatchetState(sessionId: String, state: SessionChainState) {
        val prefs = appContext?.getSharedPreferences(RATCHET_PREFS, Context.MODE_PRIVATE) ?: return
        val payload = JSONObject().apply {
            put("rootKeySeed", state.rootKeySeed?.let { Base64.encodeToString(it, Base64.NO_WRAP) } ?: "")
            put("recvChainSeed", state.recvChainSeed?.let { Base64.encodeToString(it, Base64.NO_WRAP) } ?: "")
            put("sendChainSeed", state.sendChainSeed?.let { Base64.encodeToString(it, Base64.NO_WRAP) } ?: "")
            put("recvChainCounter", state.recvChainCounter)
            put("sendChainCounter", state.sendChainCounter)
            put("updatedAtMs", System.currentTimeMillis())
        }.toString()
        prefs.edit().putString(ratchetStateKey(sessionId), payload).commit()
    }

    private fun ratchetMixChainKey(sessionId: String, baseKey: ByteArray, direction: String, counter: Int): ByteArray {
        val loadedState = loadPersistentRatchetState(sessionId)
        val state = ratchetStore.compute(sessionId) { _, existing ->
            if (existing == null) {
                loadedState ?: SessionChainState()
            } else if (loadedState != null && loadedState.recvChainCounter > existing.recvChainCounter) {
                existing.rootKeySeed = loadedState.rootKeySeed
                existing.recvChainSeed = loadedState.recvChainSeed
                existing.sendChainSeed = loadedState.sendChainSeed
                existing.recvChainCounter = loadedState.recvChainCounter
                existing.sendChainCounter = loadedState.sendChainCounter
                existing
            } else {
                existing
            }
        } ?: SessionChainState()
        synchronized(state) {
            val isRecv = direction == "s2c"
            val rootPrev = state.rootKeySeed ?: sha256(baseKey + "root-init".toByteArray(Charsets.UTF_8)).copyOfRange(0, 32)
            val dhMaterial = sha256(baseKey + direction.toByteArray(Charsets.UTF_8) + counter.toString().toByteArray(Charsets.UTF_8))
            val (rootNext, chainInit) = kdfRk(rootPrev, dhMaterial)

            // Bridge coherence: each s2c decrypt must derive from the current message base key.
            // Do not reuse persisted recv/send chain seed across independent envelopes because
            // the bridge computes `_ratchet_mix_chain_key(session_id, reply_key, "s2c", counter)`
            // from the current reply/base key, not from the previously advanced envelope seed.
            val currentChain = if (direction == "s2c") baseKey else (state.sendChainSeed ?: chainInit)

            val (chainNext, _) = kdfCk(currentChain)

            if (isRecv) {
                state.recvChainSeed = chainNext
                state.recvChainCounter += 1
            } else {
                state.sendChainSeed = chainNext
                state.sendChainCounter += 1
            }
            state.rootKeySeed = rootNext
            persistRatchetState(sessionId, state)
            return chainNext
        }
    }

    private fun kdfRk(rootKey: ByteArray, dhOut: ByteArray): Pair<ByteArray, ByteArray> {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(rootKey, "HmacSHA256"))
        val prk = mac.doFinal(dhOut)

        mac.init(SecretKeySpec(prk, "HmacSHA256"))
        val rootNext = mac.doFinal("KDF_RK:root".toByteArray(Charsets.UTF_8)).copyOfRange(0, 32)

        mac.init(SecretKeySpec(prk, "HmacSHA256"))
        val chainInit = mac.doFinal("KDF_RK:chain".toByteArray(Charsets.UTF_8)).copyOfRange(0, 32)

        return Pair(rootNext, chainInit)
    }

    private fun kdfCk(chainKey: ByteArray): Pair<ByteArray, ByteArray> {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(chainKey, "HmacSHA256"))
        val chainNext = mac.doFinal("KDF_CK:chain".toByteArray(Charsets.UTF_8)).copyOfRange(0, 32)

        mac.init(SecretKeySpec(chainKey, "HmacSHA256"))
        val messageKey = mac.doFinal("KDF_CK:msg".toByteArray(Charsets.UTF_8)).copyOfRange(0, 32)

        return Pair(chainNext, messageKey)
    }

    private fun sha256(bytes: ByteArray): ByteArray = MessageDigest.getInstance("SHA-256").digest(bytes)

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
