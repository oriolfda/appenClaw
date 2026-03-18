package com.aigor.app

import android.Manifest
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaPlayer
import android.media.MediaRecorder
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.text.Editable
import android.text.TextWatcher
import android.util.Base64
import android.view.MotionEvent
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
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
import java.io.File
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
    private lateinit var composerRow: LinearLayout
    private lateinit var clipButton: ImageButton
    private lateinit var cameraButton: ImageButton
    private lateinit var messageEdit: EditText
    private lateinit var statusText: TextView
    private lateinit var chatRecycler: RecyclerView
    private lateinit var sendButton: ImageButton
    private lateinit var pendingAttachmentRow: LinearLayout
    private lateinit var pendingAttachmentPreview: ImageView
    private lateinit var pendingAttachmentText: TextView
    private lateinit var cancelAttachmentButton: Button
    private lateinit var playLastAudioButton: Button
    private lateinit var micButton: ImageButton
    private lateinit var recordingControlsRow: LinearLayout
    private lateinit var recordDeleteButton: ImageButton
    private lateinit var recordPauseButton: ImageButton
    private lateinit var recordSendButton: ImageButton
    private lateinit var recordTimerText: TextView
    private lateinit var recordDotsText: TextView

    private lateinit var adapter: ChatAdapter
    private val messages = mutableListOf<ChatMessage>()
    private var pendingAttachment: AttachmentData? = null
    private var lastSentAudioFile: File? = null
    private var mediaPlayer: MediaPlayer? = null

    private var mediaRecorder: MediaRecorder? = null
    private var currentRecordingFile: File? = null
    private var isRecording = false
    private var isRecordingPaused = false
    private var isRecordingLocked = false
    private var micStartY = 0f
    private var micStartX = 0f
    private var recordingStartMs = 0L
    private val recordingHandler = Handler(Looper.getMainLooper())

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

    private val requestAudioPermissionLauncher = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            startPressRecording()
        } else {
            statusText.text = "Cal permís de micròfon"
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        rootLayout = findViewById(R.id.rootLayout)
        titleText = findViewById(R.id.titleText)
        overflowMenuButton = findViewById(R.id.overflowMenuButton)
        composerRow = findViewById(R.id.composerRow)
        clipButton = findViewById(R.id.clipButton)
        cameraButton = findViewById(R.id.cameraButton)
        messageEdit = findViewById(R.id.messageEdit)
        statusText = findViewById(R.id.statusText)
        chatRecycler = findViewById(R.id.chatRecycler)
        sendButton = findViewById(R.id.sendButton)
        pendingAttachmentRow = findViewById(R.id.pendingAttachmentRow)
        pendingAttachmentPreview = findViewById(R.id.pendingAttachmentPreview)
        pendingAttachmentText = findViewById(R.id.pendingAttachmentText)
        cancelAttachmentButton = findViewById(R.id.cancelAttachmentButton)
        playLastAudioButton = findViewById(R.id.playLastAudioButton)
        micButton = findViewById(R.id.micButton)
        recordingControlsRow = findViewById(R.id.recordingControlsRow)
        recordDeleteButton = findViewById(R.id.recordDeleteButton)
        recordPauseButton = findViewById(R.id.recordPauseButton)
        recordSendButton = findViewById(R.id.recordSendButton)
        recordTimerText = findViewById(R.id.recordTimerText)
        recordDotsText = findViewById(R.id.recordDotsText)

        val theme = currentTheme()
        adapter = ChatAdapter(messages, theme)
        chatRecycler.layoutManager = LinearLayoutManager(this)
        chatRecycler.adapter = adapter
        applyTheme(theme)

        loadHistory()
        consumeSharedText(intent)
        updatePendingAttachmentUi()
        updateComposerActionButton()

        messageEdit.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = Unit
            override fun afterTextChanged(s: Editable?) {
                updateComposerActionButton()
            }
        })

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
                    R.id.menu_about -> {
                        showAboutDialog()
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

        clipButton.setOnClickListener {
            pickMediaLauncher.launch("*/*")
        }

        cameraButton.setOnClickListener {
            takePicturePreviewLauncher.launch(null)
        }

        cameraButton.setOnLongClickListener {
            val intent = Intent(MediaStore.ACTION_VIDEO_CAPTURE)
            captureVideoLauncher.launch(intent)
            true
        }

        cancelAttachmentButton.setOnClickListener {
            pendingAttachment = null
            updatePendingAttachmentUi()
            statusText.text = "Adjunt eliminat"
        }

        playLastAudioButton.setOnClickListener {
            val f = lastSentAudioFile
            if (f != null && f.exists()) {
                playLocalAudio(f)
            } else {
                statusText.text = "No hi ha àudio recent"
            }
        }

        micButton.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    micStartY = event.rawY
                    micStartX = event.rawX
                    ensureAudioPermissionAndStart()
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    if (isRecording && !isRecordingLocked) {
                        val deltaUp = micStartY - event.rawY
                        val deltaLeft = micStartX - event.rawX

                        if (deltaLeft > 120f) {
                            cancelRecording()
                            statusText.text = "Gravació cancel·lada (lliscar esquerra)"
                            return@setOnTouchListener true
                        }

                        if (deltaUp > 140f) {
                            isRecordingLocked = true
                            statusText.text = "Enregistrament bloquejat 🔒"
                        }
                    }
                    true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    if (isRecording && !isRecordingLocked) {
                        stopRecordingAndAttach(sendNow = true)
                    }
                    true
                }
                else -> false
            }
        }

        recordDeleteButton.setOnClickListener {
            cancelRecording()
        }

        recordPauseButton.setOnClickListener {
            togglePauseRecording()
        }

        recordSendButton.setOnClickListener {
            if (isRecording) stopRecordingAndAttach(sendNow = true)
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

            val attachmentToSend = pendingAttachment
            if (attachmentToSend?.mime?.startsWith("audio/") == true) {
                try {
                    val bytes = Base64.decode(attachmentToSend.base64, Base64.DEFAULT)
                    val f = File(cacheDir, "last-sent-audio-${System.currentTimeMillis()}.m4a")
                    f.writeBytes(bytes)
                    lastSentAudioFile = f
                    playLastAudioButton.visibility = View.VISIBLE
                } catch (_: Exception) {
                }
            }

            sendToOpenClaw(endpoint, token, message, attachmentToSend)
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

    override fun onDestroy() {
        super.onDestroy()
        if (isRecording) {
            cancelRecording()
        } else {
            cleanupRecorderState()
        }
        try { mediaPlayer?.release() } catch (_: Exception) {}
        mediaPlayer = null
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

    private fun playLocalAudio(file: File) {
        try {
            mediaPlayer?.release()
            mediaPlayer = MediaPlayer().apply {
                setDataSource(file.absolutePath)
                setOnPreparedListener { it.start() }
                setOnCompletionListener { mp -> mp.release(); mediaPlayer = null }
                prepareAsync()
            }
            statusText.text = "Reproduint àudio..."
        } catch (e: Exception) {
            statusText.text = "No s'ha pogut reproduir l'àudio: ${e.message}"
        }
    }

    private fun tryPlayRemoteAudio(url: String) {
        val u = url.lowercase()
        val looksAudio = u.endsWith(".mp3") || u.endsWith(".m4a") || u.endsWith(".wav") || u.endsWith(".ogg") || u.contains("audio")
        if (!looksAudio) return
        try {
            mediaPlayer?.release()
            mediaPlayer = MediaPlayer().apply {
                setDataSource(url)
                setOnPreparedListener { it.start() }
                setOnCompletionListener { mp -> mp.release(); mediaPlayer = null }
                prepareAsync()
            }
            statusText.text = "Reproduint resposta d'àudio..."
        } catch (_: Exception) {
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
            pendingAttachmentPreview.setImageResource(android.R.drawable.ic_menu_gallery)
        } else {
            pendingAttachmentRow.visibility = View.VISIBLE
            pendingAttachmentText.text = "📎 ${att.name}"

            when {
                att.mime.startsWith("image/") -> {
                    try {
                        val bytes = Base64.decode(att.base64, Base64.DEFAULT)
                        val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                        if (bmp != null) pendingAttachmentPreview.setImageBitmap(bmp)
                        else pendingAttachmentPreview.setImageResource(android.R.drawable.ic_menu_gallery)
                    } catch (_: Exception) {
                        pendingAttachmentPreview.setImageResource(android.R.drawable.ic_menu_gallery)
                    }
                }
                att.mime.startsWith("video/") -> pendingAttachmentPreview.setImageResource(android.R.drawable.ic_media_play)
                att.mime.startsWith("audio/") -> pendingAttachmentPreview.setImageResource(android.R.drawable.ic_btn_speak_now)
                else -> pendingAttachmentPreview.setImageResource(android.R.drawable.ic_menu_save)
            }
        }
        updateComposerActionButton()
    }

    private fun updateComposerActionButton() {
        val hasText = messageEdit.text?.toString()?.trim()?.isNotEmpty() == true
        val showSend = hasText || pendingAttachment != null
        sendButton.visibility = if (showSend) View.VISIBLE else View.GONE
        micButton.visibility = if (showSend) View.GONE else View.VISIBLE
    }

    private fun ensureAudioPermissionAndStart() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            startPressRecording()
        } else {
            requestAudioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    private fun startPressRecording() {
        if (isRecording) return
        try {
            val file = File(cacheDir, "voice-${System.currentTimeMillis()}.m4a")
            val rec = MediaRecorder().apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setAudioEncodingBitRate(128000)
                setAudioSamplingRate(44100)
                setOutputFile(file.absolutePath)
                prepare()
                start()
            }
            mediaRecorder = rec
            currentRecordingFile = file
            isRecording = true
            isRecordingPaused = false
            isRecordingLocked = false
            recordingStartMs = System.currentTimeMillis()
            composerRow.visibility = View.GONE
            recordingControlsRow.visibility = View.VISIBLE
            statusText.text = "🎙 Gravant... llisca amunt per bloquejar"
            startRecordingTicker()
        } catch (e: Exception) {
            statusText.text = "No s'ha pogut iniciar la gravació: ${e.message}"
            cleanupRecorderState()
        }
    }

    private fun startRecordingTicker() {
        recordingHandler.removeCallbacksAndMessages(null)
        recordingHandler.post(object : Runnable {
            override fun run() {
                if (!isRecording) return
                val elapsed = ((System.currentTimeMillis() - recordingStartMs) / 1000).toInt().coerceAtLeast(0)
                val mm = elapsed / 60
                val ss = elapsed % 60
                recordTimerText.text = String.format("%02d:%02d", mm, ss)
                recordingHandler.postDelayed(this, 500)
            }
        })
    }

    private fun togglePauseRecording() {
        val rec = mediaRecorder ?: return
        try {
            if (!isRecordingPaused) {
                rec.pause()
                isRecordingPaused = true
                recordPauseButton.setImageResource(R.drawable.ic_play_min)
                statusText.text = "Gravació en pausa"
            } else {
                rec.resume()
                isRecordingPaused = false
                recordPauseButton.setImageResource(R.drawable.ic_pause_min)
                statusText.text = "🎙 Gravant..."
            }
        } catch (_: Exception) {
            // Some devices may not support pause/resume reliably.
        }
    }

    private fun cancelRecording() {
        try {
            mediaRecorder?.stop()
        } catch (_: Exception) {
        }
        currentRecordingFile?.delete()
        cleanupRecorderState()
        statusText.text = "Gravació descartada"
    }

    private fun stopRecordingAndAttach(sendNow: Boolean) {
        val file = currentRecordingFile
        try {
            mediaRecorder?.stop()
        } catch (_: Exception) {
        }
        cleanupRecorderState()

        if (file == null || !file.exists()) {
            statusText.text = "No s'ha pogut desar l'àudio"
            return
        }

        val bytes = file.readBytes()
        pendingAttachment = AttachmentData(
            name = "voice-${System.currentTimeMillis()}.m4a",
            mime = "audio/mp4",
            base64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
        )
        updatePendingAttachmentUi()
        statusText.text = "Àudio preparat"

        if (sendNow) {
            sendButton.performClick()
        }

        file.delete()
    }

    private fun cleanupRecorderState() {
        try { mediaRecorder?.release() } catch (_: Exception) {}
        mediaRecorder = null
        currentRecordingFile = null
        isRecording = false
        isRecordingPaused = false
        isRecordingLocked = false
        recordPauseButton.setImageResource(R.drawable.ic_pause_min)
        recordTimerText.text = "0:00"
        recordingControlsRow.visibility = View.GONE
        composerRow.visibility = View.VISIBLE
        recordingHandler.removeCallbacksAndMessages(null)
        updateComposerActionButton()
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
        clipButton.setColorFilter(theme.sendTint)
        cameraButton.setColorFilter(theme.sendTint)
        micButton.backgroundTintList = android.content.res.ColorStateList.valueOf(theme.sendTint)
        micButton.setColorFilter(theme.sendText)
        sendButton.backgroundTintList = android.content.res.ColorStateList.valueOf(theme.sendTint)
        sendButton.setColorFilter(theme.sendText)
        recordDeleteButton.setColorFilter(theme.statusColor)
        recordPauseButton.setColorFilter(0xFFFF4D67.toInt())
        recordSendButton.setColorFilter(0xFF04130A.toInt())
        recordTimerText.setTextColor(theme.statusColor)
        recordDotsText.setTextColor(theme.statusColor)
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
                    val mediaUrl = try {
                        JSONObject(body).optString("mediaUrl", "")
                    } catch (_: Exception) { "" }
                    if (mediaUrl.isNotBlank()) {
                        tryPlayRemoteAudio(mediaUrl)
                    }
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

    private fun showAboutDialog() {
        val pkg = packageManager.getPackageInfo(packageName, 0)
        val versionName = pkg.versionName ?: "?"
        val versionCode = pkg.longVersionCode

        val info = buildString {
            appendLine("AIGOR App")
            appendLine("Versió: $versionName ($versionCode)")
            appendLine("Bridge: OpenClaw /chat + /status")
            appendLine("Funcions: xat, context, adjunts (imatge/vídeo/àudio)")
            appendLine("")
            appendLine("Repo: aigor-app")
        }
        AlertDialog.Builder(this)
            .setTitle("Quant a")
            .setMessage(info)
            .setPositiveButton("Tancar", null)
            .show()
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
