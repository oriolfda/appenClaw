package com.aigor.app

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class ChatAdapter(private val items: MutableList<ChatMessage>) : RecyclerView.Adapter<ChatAdapter.MessageVH>() {

    companion object {
        private const val VIEW_USER = 1
        private const val VIEW_BOT = 2
    }

    class MessageVH(view: View) : RecyclerView.ViewHolder(view) {
        val text: TextView = view.findViewById(R.id.messageText)
    }

    override fun getItemViewType(position: Int): Int {
        return if (items[position].role == "user") VIEW_USER else VIEW_BOT
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): MessageVH {
        val layout = if (viewType == VIEW_USER) R.layout.item_message_user else R.layout.item_message_bot
        val view = LayoutInflater.from(parent.context).inflate(layout, parent, false)
        return MessageVH(view)
    }

    override fun onBindViewHolder(holder: MessageVH, position: Int) {
        holder.text.text = items[position].text
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
}
