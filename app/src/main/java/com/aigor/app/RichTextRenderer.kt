package com.aigor.app

import android.text.Spanned
import android.text.method.LinkMovementMethod
import android.widget.TextView
import androidx.core.text.HtmlCompat

object RichTextRenderer {

    private val codeFenceRegex = Regex("```([a-zA-Z0-9_+-]*)\\n([\\s\\S]*?)```")

    fun bind(textView: TextView, raw: String) {
        val html = toSafeHtml(raw)
        val spanned: Spanned = HtmlCompat.fromHtml(html, HtmlCompat.FROM_HTML_MODE_LEGACY)
        textView.text = spanned
        textView.movementMethod = LinkMovementMethod.getInstance()
    }

    private fun toSafeHtml(raw: String): String {
        val noDanger = raw
            .replace(Regex("<\\s*script[\\s\\S]*?<\\s*/\\s*script\\s*>", RegexOption.IGNORE_CASE), "")
            .replace(Regex("<\\s*style[\\s\\S]*?<\\s*/\\s*style\\s*>", RegexOption.IGNORE_CASE), "")
            .replace(Regex("on[a-zA-Z]+\\s*=\\s*\"[^\"]*\"", RegexOption.IGNORE_CASE), "")
            .replace(Regex("on[a-zA-Z]+\\s*=\\s*'[^']*'", RegexOption.IGNORE_CASE), "")
            .replace(Regex("javascript:", RegexOption.IGNORE_CASE), "")

        // Preserve fenced code blocks as <pre><code>.
        val blocks = mutableListOf<String>()
        val withPlaceholders = codeFenceRegex.replace(noDanger) { m ->
            val lang = m.groupValues[1].trim()
            val code = escapeHtml(m.groupValues[2])
            val block = "<pre><code data-lang=\"$lang\">$code</code></pre>"
            blocks.add(block)
            "@@CODE_BLOCK_${blocks.lastIndex}@@"
        }

        var txt = escapeHtml(withPlaceholders)

        // Minimal markdown support
        txt = txt
            .replace(Regex("\\*\\*(.+?)\\*\\*"), "<b>$1</b>")
            .replace(Regex("(^|\\s)_(.+?)_($|\\s)"), "$1<i>$2</i>$3")
            .replace(Regex("`([^`]+)`"), "<code>$1</code>")
            .replace(Regex("\\[(.+?)\\]\\((https?://[^)]+)\\)"), "<a href=\"$2\">$1</a>")

        // Restore code blocks
        blocks.forEachIndexed { i, block ->
            txt = txt.replace("@@CODE_BLOCK_$i@@", block)
        }

        // Line breaks
        txt = txt.replace("\n", "<br>")

        return txt
    }

    private fun escapeHtml(s: String): String {
        return s
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\"", "&quot;")
            .replace("'", "&#39;")
    }
}
