package com.aigor.app

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.animation.AlphaAnimation
import android.view.animation.Animation
import android.widget.TextView
import android.widget.Toast
import androidx.recyclerview.widget.RecyclerView

class ChatAdapter(
    private val items: MutableList<ChatMessage>,
    private var theme: ThemeManager.UiTheme,
    private val onMessageClick: ((ChatMessage) -> Unit)? = null,
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    private var playingMessageTs: Long? = null

    companion object {
        private const val VIEW_USER = 1
        private const val VIEW_BOT = 2
        private const val VIEW_TYPING = 3
    }

    class MessageVH(view: View) : RecyclerView.ViewHolder(view) {
        val text: TextView = view.findViewById(R.id.messageText)
    }

    class TypingVH(view: View) : RecyclerView.ViewHolder(view) {
        val d1: TextView = view.findViewById(R.id.dot1)
        val d2: TextView = view.findViewById(R.id.dot2)
        val d3: TextView = view.findViewById(R.id.dot3)
    }

    override fun getItemViewType(position: Int): Int {
        return when (items[position].role) {
            "user" -> VIEW_USER
            "typing" -> VIEW_TYPING
            else -> VIEW_BOT
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return when (viewType) {
            VIEW_USER -> MessageVH(inflater.inflate(R.layout.item_message_user, parent, false))
            VIEW_TYPING -> TypingVH(inflater.inflate(R.layout.item_message_typing, parent, false))
            else -> MessageVH(inflater.inflate(R.layout.item_message_bot, parent, false))
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        when (holder) {
            is MessageVH -> {
                val item = items[position]
                if (item.role == "user") {
                    holder.text.setBackgroundResource(theme.userBubble)
                    holder.text.setTextColor(theme.userText)
                } else {
                    holder.text.setBackgroundResource(theme.botBubble)
                    holder.text.setTextColor(theme.botText)
                }
                if (!item.audioPath.isNullOrBlank() || !item.audioUrl.isNullOrBlank() || !item.ttsText.isNullOrBlank()) {
                    val icon = if (playingMessageTs == item.ts) "⏸" else "▶"
                    RichTextRenderer.bind(holder.text, "$icon ${item.text}")
                    holder.text.setOnClickListener { onMessageClick?.invoke(item) }
                } else {
                    RichTextRenderer.bind(holder.text, item.text)
                    holder.text.setOnClickListener(null)
                }

                holder.text.setOnLongClickListener {
                    val ctx = holder.text.context
                    val clipboard = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    clipboard.setPrimaryClip(ClipData.newPlainText("aigor-message", item.text))
                    Toast.makeText(ctx, "Copiat", Toast.LENGTH_SHORT).show()
                    true
                }
            }
            is TypingVH -> {
                val bubble = holder.itemView.findViewById<View>(R.id.typingBubble)
                bubble?.setBackgroundResource(theme.botBubble)
                holder.d1.setTextColor(theme.typingDots)
                holder.d2.setTextColor(theme.typingDots)
                holder.d3.setTextColor(theme.typingDots)
                startTypingAnimation(holder)
            }
        }
    }

    private fun startTypingAnimation(holder: TypingVH) {
        animateDot(holder.d1, 0)
        animateDot(holder.d2, 160)
        animateDot(holder.d3, 320)
    }

    private fun animateDot(view: TextView, offset: Long) {
        val anim = AlphaAnimation(0.25f, 1f).apply {
            duration = 450
            repeatMode = Animation.REVERSE
            repeatCount = Animation.INFINITE
            startOffset = offset
        }
        view.startAnimation(anim)
    }

    override fun getItemCount(): Int = items.size

    fun add(message: ChatMessage) {
        items.add(message)
        notifyItemInserted(items.lastIndex)
    }

    fun replaceLast(message: ChatMessage) {
        if (items.isNotEmpty()) {
            items[items.lastIndex] = message
            notifyItemChanged(items.lastIndex)
        }
    }

    fun setTheme(newTheme: ThemeManager.UiTheme) {
        theme = newTheme
        notifyDataSetChanged()
    }

    fun setPlayingMessage(ts: Long?) {
        playingMessageTs = ts
        notifyDataSetChanged()
    }
}
