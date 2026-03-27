package com.aigor.app

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import java.text.DateFormat
import java.util.Date

class ConversationListAdapter(
    private var items: List<ConversationThread>,
    private var activeThreadId: String,
    private val titleFor: (ConversationThread) -> String,
    private val onSelect: (ConversationThread) -> Unit,
) : RecyclerView.Adapter<ConversationListAdapter.VH>() {

    private val dateFmt = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT)

    class VH(view: View) : RecyclerView.ViewHolder(view) {
        val title: TextView = view.findViewById(R.id.conversationTitle)
        val meta: TextView = view.findViewById(R.id.conversationMeta)
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
        holder.itemView.alpha = if (active) 1f else 0.9f
        holder.itemView.setOnClickListener { onSelect(item) }
    }

    fun update(items: List<ConversationThread>, activeThreadId: String) {
        this.items = items
        this.activeThreadId = activeThreadId
        notifyDataSetChanged()
    }
}
