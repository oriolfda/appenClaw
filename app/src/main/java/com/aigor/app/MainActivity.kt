package com.aigor.app

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.PopupMenu
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.regex.Pattern
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {

    private lateinit var messageEdit: EditText
    private lateinit var statusText: TextView
    private lateinit var chatRecycler: RecyclerView
    private lateinit var adapter: ChatAdapter
    private val messages = mutableListOf<ChatMessage>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        messageEdit = findViewById(R.id.messageEdit)
        statusText = findViewById(R.id.statusText)
        chatRecycler = findViewById(R.id.chatRecycler)

        adapter = ChatAdapter(messages)
        chatRecycler.layoutManager = LinearLayoutManager(this)
        chatRecycler.adapter = adapter

        loadHistory()
        consumeSharedText(intent)

        val sendButton: Button = findViewById(R.id.sendButton)
        val overflowMenuButton: Button = findViewById(R.id.overflowMenuButton)

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
            if (message.isBlank()) {
                return@setOnClickListener
            }

            addMessage(ChatMessage("user", message))
            messageEdit.setText("")
            addMessage(ChatMessage("typing", ""))
            sendToOpenClaw(endpoint, token, message)
        }
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

    private fun extractUrls(text: String): List<String> {
        val pattern = Pattern.compile("(https?://[^\\s]+)")
        val matcher = pattern.matcher(text)
        val urls = mutableListOf<String>()
        while (matcher.find()) matcher.group(1)?.let { urls.add(it) }
        return urls.distinct()
    }

    private fun sendToOpenClaw(endpoint: String, token: String, message: String) {
        statusText.text = "Estat: enviant..."

        thread {
            try {
                val urls = extractUrls(message)
                val payloadText = if (urls.isEmpty()) message else "$message\n\nURLs detectades: ${urls.joinToString(", ")}" 
                val payload = JSONObject().apply {
                    put("message", payloadText)
                    put("sessionId", "aigor-app-chat")
                }

                val conn = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Authorization", "Bearer $token")
                    connectTimeout = 15000
                    readTimeout = 20000
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
            when {
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
