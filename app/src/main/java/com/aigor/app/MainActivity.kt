package com.aigor.app

import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.util.Base64
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.ByteArrayOutputStream
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.regex.Pattern
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {

    data class AttachmentData(
        val name: String,
        val mime: String,
        val base64: String,
    )

    private lateinit var rootLayout: View
    private lateinit var titleText: TextView
    private lateinit var overflowMenuButton: ImageButton
    private lateinit var attachButton: Button
    private lateinit var messageEdit: EditText
    private lateinit var statusText: TextView
    private lateinit var chatRecycler: RecyclerView
    private lateinit var sendButton: Button
    private lateinit var pendingAttachmentRow: LinearLayout
    private lateinit var pendingAttachmentText: TextView
    private lateinit var cancelAttachmentButton: Button
    private lateinit var adapter: ChatAdapter
    private val messages = mutableListOf<ChatMessage>()
    private var pendingAttachment: AttachmentData? = null

    private val pickMediaLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        if (uri != null) handlePickedMedia(uri)
    }

    private val takePicturePreviewLauncher = registerForActivityResult(ActivityResultContracts.TakePicturePreview()) { bitmap: Bitmap? ->
        if (bitmap != null) {
            val b64 = bitmapToBase64(bitmap)
            pendingAttachment = AttachmentData(name = "camera-photo.jpg", mime = "image/jpeg", base64 = b64)
            updatePendingAttachmentUi()
            statusText.text = "Foto preparada"
        }
    }

    private val captureVideoLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
        val uri = res.data?.data
        if (uri != null) handlePickedMedia(uri)
    }

    private val recordAudioLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
        val uri = res.data?.data
        if (uri != null) handlePickedMedia(uri)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        rootLayout = findViewById(R.id.rootLayout)
        titleText = findViewById(R.id.titleText)
        overflowMenuButton = findViewById(R.id.overflowMenuButton)
        attachButton = findViewById(R.id.attachButton)
        messageEdit = findViewById(R.id.messageEdit)
        statusText = findViewById(R.id.statusText)
        chatRecycler = findViewById(R.id.chatRecycler)
        sendButton = findViewById(R.id.sendButton)
        pendingAttachmentRow = findViewById(R.id.pendingAttachmentRow)
        pendingAttachmentText = findViewById(R.id.pendingAttachmentText)
        cancelAttachmentButton = findViewById(R.id.cancelAttachmentButton)

        val theme = currentTheme()
        adapter = ChatAdapter(messages, theme)
        chatRecycler.layoutManager = LinearLayoutManager(this)
        chatRecycler.adapter = adapter
        applyTheme(theme)

        loadHistory()
        consumeSharedText(intent)
        updatePendingAttachmentUi()

        overflowMenuButton.setOnClickListener { anchor ->
            val popup = PopupMenu(this, anchor)
            popup.menuInflater.inflate(R.menu.main_overflow_menu, popup.menu)
            popup.setOnMenuItemClickListener { item ->
                when (item.itemId) {
                    R.id.menu_status -> {
                        fetchContextStatus()
                        true
                    }
                    R.id.menu_settings -> {
                        startActivity(Intent(this, SettingsActivity::class.java))
                        true
                    }
                    R.id.menu_clear_chat -> {
                        messages.clear()
                        adapter.notifyDataSetChanged()
                        saveHistory()
                        statusText.text = "Estat: xat netejat"
                        true
                    }
                    else -> false
                }
            }
            popup.show()
        }

        attachButton.setOnClickListener { anchor ->
            val popup = PopupMenu(this, anchor)
            popup.menu.add(0, 1, 0, "Fer foto")
            popup.menu.add(0, 2, 1, "Gravar vídeo")
            popup.menu.add(0, 3, 2, "Gravar àudio")
            popup.menu.add(0, 4, 3, "Triar fitxer")
            popup.setOnMenuItemClickListener { item ->
                when (item.itemId) {
                    1 -> {
                        takePicturePreviewLauncher.launch(null)
                        true
                    }
                    2 -> {
                        val intent = Intent(MediaStore.ACTION_VIDEO_CAPTURE)
                        captureVideoLauncher.launch(intent)
                        true
                    }
                    3 -> {
                        val intent = Intent(MediaStore.Audio.Media.RECORD_SOUND_ACTION)
                        recordAudioLauncher.launch(intent)
                        true
                    }
                    4 -> {
                        pickMediaLauncher.launch("*/*")
                        true
                    }
                    else -> false
                }
            }
            popup.show()
        }

        cancelAttachmentButton.setOnClickListener {
            pendingAttachment = null
            updatePendingAttachmentUi()
            statusText.text = "Adjunt eliminat"
        }

        sendButton.setOnClickListener {
            val prefs = getSharedPreferences("aigor_prefs", MODE_PRIVATE)
            val endpoint = prefs.getString("openclaw_endpoint", "").orEmpty().trim()
            val token = prefs.getString("openclaw_hook_token", "").orEmpty().trim()
            val message = messageEdit.text.toString().trim()

            if (endpoint.isBlank()) {
                statusText.text = "Estat: falta endpoint (Settings)"
                return@setOnClickListener
            }
            if (token.isBlank()) {
                statusText.text = "Estat: falta token (Settings)"
                return@setOnClickListener
            }
            if (message.isBlank() && pendingAttachment == null) {
                return@setOnClickListener
            }

            val previewText = buildString {
                if (message.isNotBlank()) append(message)
                pendingAttachment?.let {
                    if (isNotBlank()) append("\n")
                    append("📎 ${it.name}")
                }
            }

            addMessage(ChatMessage("user", previewText.ifBlank { "(adjunt)" }))
            messageEdit.setText("")
            addMessage(ChatMessage("typing", ""))
            sendToOpenClaw(endpoint, token, message, pendingAttachment)
            pendingAttachment = null
            updatePendingAttachmentUi()
        }
    }

    override fun onResume() {
        super.onResume()
        val theme = currentTheme()
        applyTheme(theme)
        adapter.setTheme(theme)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        consumeSharedText(intent)
    }

    private fun consumeSharedText(intent: Intent?) {
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            val shared = intent.getStringExtra(Intent.EXTRA_TEXT)?.trim().orEmpty()
            if (shared.isNotBlank()) {
                val current = messageEdit.text.toString().trim()
                val combined = if (current.isBlank()) shared else "$current\n\n$shared"
                messageEdit.setText(combined)
                statusText.text = "Estat: text compartit carregat"
            }
        }
    }

    private fun handlePickedMedia(uri: Uri) {
        try {
            val mime = contentResolver.getType(uri).orEmpty()
            if (!(mime.startsWith("image/") || mime.startsWith("video/") || mime.startsWith("audio/"))) {
                statusText.text = "Només imatge, vídeo o àudio"
                return
            }

            val name = queryName(uri) ?: "adjunt"
            val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: run {
                statusText.text = "No s'ha pogut llegir el fitxer"
                return
            }
            if (bytes.size > 12 * 1024 * 1024) {
                statusText.text = "Fitxer massa gran (>12MB)"
                return
            }

            val b64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
            pendingAttachment = AttachmentData(name = name, mime = mime, base64 = b64)
            updatePendingAttachmentUi()
            statusText.text = "Adjunt preparat: $name"
        } catch (e: Exception) {
            statusText.text = "Error adjunt: ${e.message}"
        }
    }

    private fun queryName(uri: Uri): String? {
        return contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (idx >= 0 && cursor.moveToFirst()) cursor.getString(idx) else null
        }
    }

    private fun bitmapToBase64(bitmap: Bitmap): String {
        val out = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 90, out)
        return Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
    }

    private fun updatePendingAttachmentUi() {
        val att = pendingAttachment
        if (att == null) {
            pendingAttachmentRow.visibility = View.GONE
            attachButton.text = "+"
        } else {
            pendingAttachmentRow.visibility = View.VISIBLE
            pendingAttachmentText.text = "📎 ${att.name}"
            attachButton.text = "📎"
        }
    }

    private fun currentTheme(): ThemeManager.UiTheme {
        val prefs = getSharedPreferences("aigor_prefs", MODE_PRIVATE)
        return ThemeManager.byId(prefs.getString(ThemeManager.PREF_KEY, "html_match"))
    }

    private fun applyTheme(theme: ThemeManager.UiTheme) {
        rootLayout.setBackgroundColor(theme.screenBg)
        titleText.setTextColor(theme.titleColor)
        statusText.setTextColor(theme.statusColor)
        overflowMenuButton.setColorFilter(theme.menuDotsColor)
        overflowMenuButton.setBackgroundColor(android.graphics.Color.TRANSPARENT)
        messageEdit.setTextColor(theme.messageTextColor)
        messageEdit.setHintTextColor(theme.messageHintColor)
        messageEdit.setBackgroundResource(theme.inputBg)
        attachButton.backgroundTintList = android.content.res.ColorStateList.valueOf(0xFF1F2937.toInt())
        attachButton.setTextColor(theme.menuDotsColor)
        sendButton.backgroundTintList = android.content.res.ColorStateList.valueOf(theme.sendTint)
        sendButton.setTextColor(theme.sendText)
    }

    private fun extractUrls(text: String): List<String> {
        val pattern = Pattern.compile("(https?://[^\\s]+)")
        val matcher = pattern.matcher(text)
        val urls = mutableListOf<String>()
        while (matcher.find()) matcher.group(1)?.let { urls.add(it) }
        return urls.distinct()
    }

    private fun sendToOpenClaw(endpoint: String, token: String, message: String, attachment: AttachmentData?) {
        statusText.text = "Estat: enviant..."

        thread {
            try {
                val urls = extractUrls(message)
                val payloadText = if (urls.isEmpty()) message else "$message\n\nURLs detectades: ${urls.joinToString(", ")}" 
                val payload = JSONObject().apply {
                    put("message", payloadText)
                    put("sessionId", "aigor-app-chat")
                    attachment?.let {
                        put("attachment", JSONObject().apply {
                            put("name", it.name)
                            put("mime", it.mime)
                            put("dataBase64", it.base64)
                        })
                    }
                }

                val conn = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Authorization", "Bearer $token")
                    connectTimeout = 20000
                    readTimeout = 120000
                    doOutput = true
                }

                OutputStreamWriter(conn.outputStream).use { it.write(payload.toString()) }

                val code = conn.responseCode
                val body = try {
                    if (code in 200..299) conn.inputStream.bufferedReader().use(BufferedReader::readText)
                    else conn.errorStream?.bufferedReader()?.use(BufferedReader::readText).orEmpty()
                } catch (_: Exception) { "" }

                runOnUiThread {
                    val assistantText = parseAssistantText(body, code)
                    adapter.replaceLast(ChatMessage("assistant", assistantText))
                    statusText.text = if (code in 200..299) "Estat: enviat OK ($code)" else "Estat: error HTTP $code"
                    saveHistory()
                    scrollBottom()
                }
                conn.disconnect()
            } catch (e: Exception) {
                runOnUiThread {
                    adapter.replaceLast(ChatMessage("assistant", "Error de connexió: ${e.message}"))
                    statusText.text = "Estat: error ${e.message}"
                    saveHistory()
                    scrollBottom()
                }
            }
        }
    }

    private fun fetchContextStatus() {
        val prefs = getSharedPreferences("aigor_prefs", MODE_PRIVATE)
        val endpoint = prefs.getString("openclaw_endpoint", "").orEmpty().trim()
        val token = prefs.getString("openclaw_hook_token", "").orEmpty().trim()
        if (endpoint.isBlank() || token.isBlank()) {
            statusText.text = "Estat: configura endpoint/token a Settings"
            return
        }

        val statusUrl = endpoint.replace("/chat", "/status")
        addMessage(ChatMessage("assistant", "Consultant estat de context..."))

        thread {
            try {
                val conn = (URL(statusUrl).openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    setRequestProperty("Authorization", "Bearer $token")
                    connectTimeout = 12000
                    readTimeout = 15000
                }
                val code = conn.responseCode
                val body = try {
                    if (code in 200..299) conn.inputStream.bufferedReader().use(BufferedReader::readText)
                    else conn.errorStream?.bufferedReader()?.use(BufferedReader::readText).orEmpty()
                } catch (_: Exception) { "" }

                runOnUiThread {
                    val msg = parseStatusText(body, code)
                    addMessage(ChatMessage("assistant", msg))
                    statusText.text = if (code in 200..299) "Estat: context rebut" else "Estat: error context ($code)"
                }
                conn.disconnect()
            } catch (e: Exception) {
                runOnUiThread {
                    addMessage(ChatMessage("assistant", "Error consultant context: ${e.message}"))
                }
            }
        }
    }

    private fun parseStatusText(body: String, code: Int): String {
        if (body.isBlank()) return "No hi ha dades de context (HTTP $code)"
        return try {
            val obj = JSONObject(body)
            if (!obj.optBoolean("ok", false)) {
                return "No s'ha pogut llegir el context: ${obj.optString("error", "error")}" 
            }
            val ctx = obj.optJSONObject("context") ?: return "Resposta de context incompleta"
            val used = ctx.optLong("usedTokens", -1)
            val max = ctx.optLong("maxTokens", -1)
            val usedPct = ctx.optDouble("usedPercent", -1.0)
            val free = ctx.optLong("freeTokens", -1)
            val freePct = ctx.optDouble("freePercent", -1.0)
            val model = ctx.optString("model", "?")

            "Context actual:\n• Model: $model\n• Ocupat: $used / $max tokens (${if (usedPct >= 0) usedPct else "?"}%)\n• Lliure: $free tokens (${if (freePct >= 0) freePct else "?"}%)"
        } catch (_: Exception) {
            "No s'ha pogut parsejar l'estat de context"
        }
    }

    private fun parseAssistantText(body: String, code: Int): String {
        if (body.isBlank()) return if (code in 200..299) "Missatge enviat ✅" else "Error HTTP $code"
        return try {
            val obj = JSONObject(body)
            val core = when {
                obj.has("reply") -> obj.optString("reply")
                obj.has("response") -> obj.optString("response")
                obj.has("message") -> obj.optString("message")
                obj.has("text") -> obj.optString("text")
                obj.has("ok") && !obj.optBoolean("ok", false) -> {
                    val err = obj.optString("error", "error desconegut")
                    val details = obj.optString("details", "")
                    "Error bridge: $err${if (details.isNotBlank()) "\n$details" else ""}"
                }
                obj.has("ok") -> "Missatge enviat ✅"
                else -> body
            }
            val mediaUrl = obj.optString("mediaUrl", "")
            if (mediaUrl.isNotBlank()) "$core\n\n🔗 Media: $mediaUrl" else core
        } catch (_: Exception) {
            body
        }
    }

    private fun addMessage(msg: ChatMessage) {
        adapter.add(msg)
        saveHistory()
        scrollBottom()
    }

    private fun scrollBottom() {
        if (messages.isNotEmpty()) chatRecycler.scrollToPosition(messages.lastIndex)
    }

    private fun loadHistory() {
        val prefs = getSharedPreferences("aigor_prefs", MODE_PRIVATE)
        val raw = prefs.getString("chat_history", "[]").orEmpty()
        messages.clear()
        try {
            val arr = JSONArray(raw)
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                val role = o.optString("role", "assistant")
                if (role != "typing") {
                    messages.add(ChatMessage(role, o.optString("text", ""), o.optLong("ts", 0L)))
                }
            }
        } catch (_: Exception) {
        }
        adapter.notifyDataSetChanged()
        scrollBottom()
    }

    private fun saveHistory() {
        val arr = JSONArray()
        messages.takeLast(200).forEach {
            arr.put(JSONObject().apply {
                put("role", it.role)
                put("text", it.text)
                put("ts", it.ts)
            })
        }
        getSharedPreferences("aigor_prefs", MODE_PRIVATE)
            .edit()
            .putString("chat_history", arr.toString())
            .apply()
    }
}
