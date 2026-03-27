package com.aigor.app

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

data class ConversationThread(
    val threadId: String,
    val sessionId: String,
    val createdAt: Long,
    val updatedAt: Long,
    val title: String? = null,
)

object ConversationStore {
    private const val PREFS_NAME = "aigor_prefs"
    private const val KEY_THREADS = "chat_threads"
    private const val KEY_ACTIVE_THREAD_ID = "chat_active_thread_id"
    private const val KEY_LEGACY_CHAT_HISTORY = "chat_history"
    private const val KEY_HISTORY_PREFIX = "chat_history_thread_"

    data class State(
        val threads: List<ConversationThread>,
        val activeThreadId: String,
    ) {
        val activeThread: ConversationThread?
            get() = threads.firstOrNull { it.threadId == activeThreadId }
    }

    fun ensureState(context: Context): State {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val threads = loadThreads(prefs)
        val activeId = prefs.getString(KEY_ACTIVE_THREAD_ID, "").orEmpty()

        val active = threads.firstOrNull { it.threadId == activeId }
        if (threads.isNotEmpty() && active != null) {
            return State(threads, active.threadId)
        }

        val fallback = threads.firstOrNull() ?: newThread()

        val normalizedThreads = if (threads.isEmpty()) listOf(fallback) else threads
        saveThreads(prefs, normalizedThreads)
        prefs.edit().putString(KEY_ACTIVE_THREAD_ID, fallback.threadId).apply()
        return State(normalizedThreads, fallback.threadId)
    }

    fun createNewAndActivate(context: Context): ConversationThread {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val now = System.currentTimeMillis()
        val current = loadThreads(prefs)
        val created = newThread(now)
        val updatedThreads = current + created
        saveThreads(prefs, updatedThreads)
        prefs.edit().putString(KEY_ACTIVE_THREAD_ID, created.threadId).apply()
        return created
    }

    fun activateThread(context: Context, threadId: String): ConversationThread? {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val threads = loadThreads(prefs)
        val target = threads.firstOrNull { it.threadId == threadId } ?: return null
        prefs.edit().putString(KEY_ACTIVE_THREAD_ID, target.threadId).apply()
        return target
    }


    fun deleteThread(context: Context, threadId: String): State {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val current = loadThreads(prefs)
        val filtered = current.filterNot { it.threadId == threadId }
        prefs.edit().remove(historyKey(threadId)).apply()
        val normalized = if (filtered.isEmpty()) listOf(newThread()) else filtered
        val currentActive = prefs.getString(KEY_ACTIVE_THREAD_ID, "").orEmpty()
        val nextActive = if (normalized.any { it.threadId == currentActive }) currentActive else normalized.first().threadId
        saveThreads(prefs, normalized)
        prefs.edit().putString(KEY_ACTIVE_THREAD_ID, nextActive).apply()
        return State(normalized, nextActive)
    }

    fun loadHistoryJson(context: Context, threadId: String): String {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val key = historyKey(threadId)
        val direct = prefs.getString(key, null)
        if (direct != null) return direct

        val legacy = prefs.getString(KEY_LEGACY_CHAT_HISTORY, null)
        if (!legacy.isNullOrBlank()) {
            prefs.edit().putString(key, legacy).apply()
            return legacy
        }

        return "[]"
    }

    fun saveHistoryJson(context: Context, threadId: String, historyJson: String) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(historyKey(threadId), historyJson).apply()
        touchThreadUpdatedAt(context, threadId)
    }


    fun suggestTitleFromHistoryJson(historyJson: String): String? {
        return try {
            val arr = JSONArray(historyJson)
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                val role = o.optString("role", "")
                val text = o.optString("text", "").trim()
                if (role == "user" && text.isNotBlank()) {
                    return summarizeTitle(text)
                }
            }
            null
        } catch (_: Exception) {
            null
        }
    }

    fun assignTitleIfMissing(context: Context, threadId: String, candidate: String) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val current = loadThreads(prefs)
        val updated = current.map { thread ->
            if (thread.threadId == threadId && thread.title.isNullOrBlank()) {
                thread.copy(title = summarizeTitle(candidate), updatedAt = System.currentTimeMillis())
            } else thread
        }
        if (updated != current) saveThreads(prefs, updated)
    }

    private fun summarizeTitle(text: String): String {
        val compact = text
            .replace(Regex("\\s+"), " ")
            .trim()
            .trim('"', '\'', '`')
        if (compact.isBlank()) return "Nou xat"
        return compact.take(48).trimEnd().let { if (compact.length > 48) "$it…" else it }
    }

    fun touchThreadUpdatedAt(context: Context, threadId: String, now: Long = System.currentTimeMillis()) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val current = loadThreads(prefs)
        if (current.isEmpty()) return

        val updated = current.map { thread ->
            if (thread.threadId == threadId) thread.copy(updatedAt = now) else thread
        }

        if (updated != current) {
            saveThreads(prefs, updated)
        }
    }

    private fun newThread(now: Long = System.currentTimeMillis()): ConversationThread {
        return ConversationThread(
            threadId = UUID.randomUUID().toString(),
            sessionId = "aigor-app-chat-${UUID.randomUUID()}",
            createdAt = now,
            updatedAt = now,
            title = null,
        )
    }

    private fun historyKey(threadId: String): String = "$KEY_HISTORY_PREFIX$threadId"

    private fun loadThreads(prefs: android.content.SharedPreferences): List<ConversationThread> {
        val raw = prefs.getString(KEY_THREADS, "[]").orEmpty()
        return try {
            val arr = JSONArray(raw)
            buildList {
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    val threadId = o.optString("threadId", "").trim()
                    val sessionId = o.optString("sessionId", "").trim()
                    if (threadId.isBlank() || sessionId.isBlank()) continue

                    add(
                        ConversationThread(
                            threadId = threadId,
                            sessionId = sessionId,
                            createdAt = o.optLong("createdAt", 0L).takeIf { it > 0 } ?: System.currentTimeMillis(),
                            updatedAt = o.optLong("updatedAt", 0L).takeIf { it > 0 } ?: System.currentTimeMillis(),
                            title = o.optString("title", "").ifBlank { null },
                        )
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun saveThreads(prefs: android.content.SharedPreferences, threads: List<ConversationThread>) {
        val arr = JSONArray()
        threads.forEach { t ->
            arr.put(JSONObject().apply {
                put("threadId", t.threadId)
                put("sessionId", t.sessionId)
                put("createdAt", t.createdAt)
                put("updatedAt", t.updatedAt)
                if (!t.title.isNullOrBlank()) put("title", t.title)
            })
        }
        prefs.edit().putString(KEY_THREADS, arr.toString()).apply()
    }
}
