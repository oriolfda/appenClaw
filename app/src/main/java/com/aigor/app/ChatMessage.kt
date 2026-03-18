package com.aigor.app

data class ChatMessage(
    val role: String, // "user" | "assistant" | "system"
    val text: String,
    val ts: Long = System.currentTimeMillis()
)
