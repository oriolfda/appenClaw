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
)

object ConversationStore {
    private const val PREFS_NAME = "aigor_prefs"
    private const val KEY_THREADS = "chat_threads"
    private const val KEY_ACTIVE_THREAD_ID = "chat_active_thread_id"

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

        val now = System.currentTimeMillis()
        val fallback = threads.firstOrNull() ?: ConversationThread(
            threadId = UUID.randomUUID().toString(),
            sessionId = "aigor-app-chat-${UUID.randomUUID()}",
            createdAt = now,
            updatedAt = now,
        )

        val normalizedThreads = if (threads.isEmpty()) listOf(fallback) else threads
        saveThreads(prefs, normalizedThreads)
        prefs.edit().putString(KEY_ACTIVE_THREAD_ID, fallback.threadId).apply()
        return State(normalizedThreads, fallback.threadId)
    }

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
            })
        }
        prefs.edit().putString(KEY_THREADS, arr.toString()).apply()
    }
}
