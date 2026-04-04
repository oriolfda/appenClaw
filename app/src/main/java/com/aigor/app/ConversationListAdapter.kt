package com.aigor.app

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import java.text.DateFormat
import java.util.Date

class ConversationListAdapter(
    private var items: List<ConversationThread>,
    private var activeThreadId: String,
    private var theme: ThemeManager.UiTheme,
    private val titleFor: (ConversationThread) -> String,
    private val onSelect: (ConversationThread) -> Unit,
    private val onDelete: (ConversationThread) -> Unit,
) : RecyclerView.Adapter<ConversationListAdapter.VH>() {

    private val dateFmt = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT)

    class VH(view: View) : RecyclerView.ViewHolder(view) {
        val title: TextView = view.findViewById(R.id.conversationTitle)
        val meta: TextView = view.findViewById(R.id.conversationMeta)
        val delete: ImageButton = view.findViewById(R.id.deleteConversationButton)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_conversation_entry, parent, false)
        return VH(view)
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = items[position]
        val active = item.threadId == activeThreadId
        holder.title.text = titleFor(item)
        holder.meta.text = if (active) {
            "Activa · ${dateFmt.format(Date(item.updatedAt))}"
        } else {
            dateFmt.format(Date(item.updatedAt))
        }
        holder.title.setTextColor(if (active) theme.titleColor else theme.messageTextColor)
        holder.meta.setTextColor(if (active) theme.sendTint else theme.statusColor)
        holder.delete.setColorFilter(theme.sendTint)
        holder.itemView.alpha = if (active) 1f else 0.92f
        holder.itemView.setBackgroundColor(if (active) theme.menuTint.takeIf { it != 0 } ?: theme.screenBg else theme.screenBg)
        holder.itemView.setOnClickListener { onSelect(item) }
        holder.delete.setOnClickListener { onDelete(item) }
    }

    fun update(items: List<ConversationThread>, activeThreadId: String, theme: ThemeManager.UiTheme = this.theme) {
        this.items = items
        this.activeThreadId = activeThreadId
        this.theme = theme
        notifyDataSetChanged()
    }
}
