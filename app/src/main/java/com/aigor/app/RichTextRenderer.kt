package com.aigor.app

import android.graphics.Color
import android.graphics.Typeface
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.method.LinkMovementMethod
import android.text.style.ForegroundColorSpan
import android.widget.TextView
import androidx.core.text.HtmlCompat

object RichTextRenderer {

    data class CodeBlock(
        val language: String?,
        val code: String,
    )

    // Supports both:
    // ```python\n...\n```
    // ```python ... ```
    private val codeFenceRegex = Regex("```([a-zA-Z0-9_+#.+-]*)\\s*([\\s\\S]*?)```")
    private val indentedCodeRegex = Regex("(?m)^(?:\\t| {4,}).+")
    private val pythonLikeLineRegex = Regex("(?m)^(def |class |import |from |for |while |if |elif |else:|try:|except |with |print\\()")

    fun bind(textView: TextView, raw: String, selectable: Boolean = true) {
        val html = toSafeHtml(raw)
        val spanned: Spanned = HtmlCompat.fromHtml(html, HtmlCompat.FROM_HTML_MODE_LEGACY)
        textView.text = spanned
        textView.movementMethod = LinkMovementMethod.getInstance()
        textView.setTextIsSelectable(selectable)

        if (looksLikeCode(raw)) {
            textView.typeface = Typeface.MONOSPACE
            textView.textSize = 14f
            textView.setHorizontallyScrolling(false)
        } else {
            textView.typeface = Typeface.DEFAULT
            textView.textSize = 16f
            textView.setHorizontallyScrolling(false)
        }
    }

    fun extractCopyableCode(raw: String): String? {
        val normalized = raw.trim()
        if (normalized.isBlank()) return null

        val fencedBlocks = codeFenceRegex
            .findAll(normalized)
            .mapNotNull { it.groupValues.getOrNull(2)?.trim('\n', '\r') }
            .filter { it.isNotBlank() }
            .toList()

        if (fencedBlocks.isNotEmpty()) {
            return fencedBlocks.joinToString("\n\n")
        }

        val hasIndentedCode = indentedCodeRegex.containsMatchIn(normalized)
        return if (looksLikeCode(normalized) || hasIndentedCode) normalized else null
    }

    fun hasScrollableCodeBlock(raw: String): Boolean {
        val normalized = raw.trim()
        if (normalized.isBlank()) return false
        if (codeFenceRegex.containsMatchIn(normalized)) return true
        val lines = normalized.lines().map { it.trimEnd() }.filter { it.isNotBlank() }
        val hasIndentedCode = indentedCodeRegex.containsMatchIn(normalized)
        val hasPythonLikeLines = lines.count { pythonLikeLineRegex.containsMatchIn(it.trimStart()) } >= 2
        val hasBracesOrTags = normalized.contains("{") || normalized.contains("}") || normalized.contains("</") || normalized.contains("<div")
        return (hasIndentedCode && looksLikeCode(normalized)) || (lines.size >= 3 && (hasPythonLikeLines || hasBracesOrTags) && looksLikeCodeBoosted(normalized, lines))
    }

    private fun looksLikeCodeBoosted(raw: String, lines: List<String>): Boolean {
        if (looksLikeCode(raw)) return true
        val punctuated = lines.count { line ->
            val t = line.trim()
            t.endsWith(":") || t.contains(" = ") || t.contains("(") || t.contains(")")
        }
        return punctuated >= 2
    }

    fun extractFirstCodeBlock(raw: String): CodeBlock? {
        val normalized = raw.trim()
        if (normalized.isBlank()) return null

        val match = codeFenceRegex.find(normalized)
        if (match != null) {
            val language = match.groupValues.getOrNull(1)?.trim()?.ifBlank { null }
            val code = match.groupValues.getOrNull(2)?.trim('\n', '\r') ?: ""
            return CodeBlock(language = language, code = code)
        }

        val copyable = extractCopyableCode(normalized) ?: return null
        val inferredLanguage = inferLanguage(copyable)
        return CodeBlock(language = inferredLanguage, code = copyable.trimEnd())
    }

    fun extractScrollableCodeText(raw: String): String {
        return extractFirstCodeBlock(raw)?.code?.trimEnd() ?: raw.trimEnd()
    }

    fun displayLanguageLabel(rawLanguage: String?): String {
        val normalized = normalizeLanguage(rawLanguage) ?: return "TEXT"
        return when (normalized) {
            "javascript" -> "JavaScript"
            "typescript" -> "TypeScript"
            "kotlin" -> "Kotlin"
            "python" -> "Python"
            "bash" -> "Bash"
            "yaml" -> "YAML"
            "json" -> "JSON"
            "html" -> "HTML"
            "css" -> "CSS"
            "xml" -> "XML"
            "sql" -> "SQL"
            "java" -> "Java"
            "c" -> "C"
            "cpp" -> "C++"
            "csharp" -> "C#"
            "php" -> "PHP"
            "ruby" -> "Ruby"
            "go" -> "Go"
            "rust" -> "Rust"
            "swift" -> "Swift"
            "markdown" -> "Markdown"
            else -> normalized.uppercase()
        }
    }

    fun buildHighlightedCode(rawLanguage: String?, code: String): SpannableStringBuilder {
        val language = normalizeLanguage(rawLanguage) ?: inferLanguage(code)
        val out = SpannableStringBuilder(code)
        if (code.isBlank()) return out

        val keywordColor = Color.parseColor("#C084FC")
        val variableColor = Color.parseColor("#93C5FD")
        val symbolColor = Color.parseColor("#FCA5A5")
        val stringColor = Color.parseColor("#86EFAC")
        val numberColor = Color.parseColor("#FCD34D")

        applyRegexColor(out, Regex("\"([^\"\\\\]|\\\\.)*\"|'([^'\\\\]|\\\\.)*'"), stringColor)
        applyRegexColor(out, Regex("(?<![A-Za-z0-9_])(\\d+(?:\\.\\d+)?)(?![A-Za-z0-9_])"), numberColor)
        applyRegexColor(out, Regex("[(){}\\[\\]=><!:+\\-/*%.,;|&]+"), symbolColor)

        val keywordRegex = when (language) {
            "python" -> Regex("\\b(def|class|import|from|return|if|elif|else|for|while|try|except|with|as|lambda|pass|raise|yield|in|is|not|and|or|None|True|False)\\b")
            "javascript", "typescript" -> Regex("\\b(function|const|let|var|return|if|else|for|while|switch|case|break|continue|import|from|export|default|async|await|new|class|extends|try|catch|finally|throw|true|false|null|undefined|interface|type|implements)\\b")
            "kotlin" -> Regex("\\b(fun|val|var|class|data|object|interface|return|if|else|when|for|while|try|catch|finally|null|true|false|package|import|override|private|public|internal)\\b")
            "json" -> Regex("\"[^\"]+\"(?=\\s*:)\\b")
            "yaml" -> Regex("(?m)^\\s*([A-Za-z0-9_.-]+):")
            "html" -> Regex("</?[A-Za-z][A-Za-z0-9:-]*|/?>")
            "css" -> Regex("(?m)^\\s*([.#]?[A-Za-z_-][A-Za-z0-9_-]*)|\\b(color|background|display|padding|margin|border|font-size|position)\\b")
            "bash" -> Regex("\\b(if|then|else|fi|for|do|done|case|esac|function|echo|export|local|return)\\b")
            "sql" -> Regex("\\b(SELECT|FROM|WHERE|INSERT|INTO|VALUES|UPDATE|DELETE|JOIN|LEFT|RIGHT|INNER|OUTER|ORDER|GROUP|BY|LIMIT|AS|AND|OR|NOT|NULL|CREATE|TABLE)\\b", RegexOption.IGNORE_CASE)
            else -> Regex("\\b(class|return|if|else|for|while|import|from|const|let|var|fun|def)\\b")
        }
        applyRegexColor(out, keywordRegex, keywordColor)

        val variableRegex = when (language) {
            "python" -> Regex("(?m)(?<=def\\s)([A-Za-z_][A-Za-z0-9_]*)|(?m)(?<=class\\s)([A-Za-z_][A-Za-z0-9_]*)|(?m)\\bself\\b|(?m)(?<!\\.)([A-Za-z_][A-Za-z0-9_]*)(?=\\s*=)")
            "javascript", "typescript" -> Regex("(?m)(?<=const\\s)([A-Za-z_$][A-Za-z0-9_$]*)|(?m)(?<=let\\s)([A-Za-z_$][A-Za-z0-9_$]*)|(?m)(?<=var\\s)([A-Za-z_$][A-Za-z0-9_$]*)|(?m)(?<=function\\s)([A-Za-z_$][A-Za-z0-9_$]*)|(?m)([A-Za-z_$][A-Za-z0-9_$]*)(?=\\s*=>)")
            "kotlin" -> Regex("(?m)(?<=fun\\s)([A-Za-z_][A-Za-z0-9_]*)|(?m)(?<=val\\s)([A-Za-z_][A-Za-z0-9_]*)|(?m)(?<=var\\s)([A-Za-z_][A-Za-z0-9_]*)|(?m)(?<=class\\s)([A-Za-z_][A-Za-z0-9_]*)")
            "json", "yaml" -> Regex("(?m)\"([^\"]+)\"(?=\\s*:)|(?m)^\\s*([A-Za-z0-9_.-]+)(?=:)" )
            else -> Regex("(?m)([A-Za-z_][A-Za-z0-9_]*)(?=\\s*=)")
        }
        applyRegexColor(out, variableRegex, variableColor)

        return out
    }

    private fun toSafeHtml(raw: String): String {
        val noDanger = raw
            .replace(Regex("<\\s*script[\\s\\S]*?<\\s*/\\s*script\\s*>", RegexOption.IGNORE_CASE), "")
            .replace(Regex("<\\s*style[\\s\\S]*?<\\s*/\\s*style\\s*>", RegexOption.IGNORE_CASE), "")
            .replace(Regex("on[a-zA-Z]+\\s*=\\s*\"[^\"]*\"", RegexOption.IGNORE_CASE), "")
            .replace(Regex("on[a-zA-Z]+\\s*=\\s*'[^']*'", RegexOption.IGNORE_CASE), "")
            .replace(Regex("javascript:", RegexOption.IGNORE_CASE), "")
            .trim()

        // Preserve fenced code blocks as <pre><code>.
        val blocks = mutableListOf<String>()
        val hadCodeFences = codeFenceRegex.containsMatchIn(noDanger)
        val withPlaceholders = codeFenceRegex.replace(noDanger) { m ->
            val lang = m.groupValues[1].trim()
            val code = escapeHtml(m.groupValues[2].trim())
            val block = "<pre><code data-lang=\"$lang\">$code</code></pre>"
            blocks.add(block)
            "@@CODE_BLOCK_${blocks.lastIndex}@@"
        }

        val hasHtmlTags = Regex("<\\s*[a-zA-Z][^>]*>").containsMatchIn(withPlaceholders)

        var txt = if (hasHtmlTags) {
            // Keep user HTML tags (already sanitized above).
            withPlaceholders
        } else {
            // Plain text/markdown path.
            escapeHtml(withPlaceholders)
        }

        // Minimal markdown support (applied mostly for non-HTML input)
        txt = txt
            .replace(Regex("\\*\\*(.+?)\\*\\*"), "<b>$1</b>")
            .replace(Regex("(^|\\s)_(.+?)_($|\\s)"), "$1<i>$2</i>$3")
            .replace(Regex("`([^`]+)`"), "<code>$1</code>")
            .replace(Regex("\\[(.+?)\\]\\((https?://[^)]+)\\)"), "<a href=\"$2\">$1</a>")

        // Restore code blocks
        blocks.forEachIndexed { i, block ->
            txt = txt.replace("@@CODE_BLOCK_$i@@", block)
        }

        // If text looks like raw code and there were no explicit fences,
        // force <pre><code> to preserve spacing.
        if (!hasHtmlTags && !hadCodeFences && looksLikeCode(noDanger)) {
            return "<pre><code>${escapeHtml(noDanger)}</code></pre>"
        }

        // Line breaks
        txt = txt.replace("\n", "<br>")

        return txt
    }

    private fun applyRegexColor(text: SpannableStringBuilder, regex: Regex, color: Int) {
        regex.findAll(text).forEach { match ->
            val start = match.range.first
            val end = match.range.last + 1
            if (start in 0 until end && end <= text.length) {
                text.setSpan(ForegroundColorSpan(color), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
        }
    }

    private fun normalizeLanguage(rawLanguage: String?): String? {
        val normalized = rawLanguage?.trim()?.lowercase()?.ifBlank { null } ?: return null
        return when (normalized) {
            "js" -> "javascript"
            "ts" -> "typescript"
            "kt", "kts" -> "kotlin"
            "py" -> "python"
            "sh", "zsh", "shell" -> "bash"
            "yml" -> "yaml"
            "c++" -> "cpp"
            "cs" -> "csharp"
            "rb" -> "ruby"
            "rs" -> "rust"
            "md" -> "markdown"
            else -> normalized
        }
    }

    private fun inferLanguage(code: String): String? {
        val t = code.trim()
        if (t.isBlank()) return null
        val lower = t.lowercase()
        return when {
            Regex("(?m)^\\s*(fun|val|var|data class|class)\\b").containsMatchIn(t) -> "kotlin"
            Regex("(?m)^\\s*(def|class|import|from)\\b").containsMatchIn(t) && t.contains(":") -> "python"
            Regex("(?m)^\\s*(const|let|function|import|export)\\b").containsMatchIn(t) || t.contains("=>") -> "javascript"
            Regex("(?m)^\\s*(interface|type|enum)\\b").containsMatchIn(t) || t.contains(": string") || t.contains(": number") -> "typescript"
            lower.contains("<html") || lower.contains("<div") || lower.contains("</") -> "html"
            Regex("(?m)^\\s*[.#a-zA-Z0-9_-]+\\s*\\{").containsMatchIn(t) -> "css"
            lower.startsWith("{") || lower.startsWith("[") -> "json"
            Regex("(?m)^\\s*[a-zA-Z0-9_-]+:\\s*").containsMatchIn(t) && !t.contains("{") -> "yaml"
            lower.contains("select ") || lower.contains("insert ") || lower.contains("update ") -> "sql"
            Regex("(?m)^\\s*(#!/bin/(ba)?sh|echo |export |if \\[|fi$)").containsMatchIn(t) -> "bash"
            else -> null
        }
    }

    private fun looksLikeCode(s: String): Boolean {
        val t = s.trim()
        if (t.contains("```") || t.contains("<pre") || t.contains("<code")) return true
        if (inferLanguage(t) != null) return true
        val lines = t.lines()
        if (lines.size < 3) return false
        var score = 0
        val markers = listOf("def ", "class ", "return ", "{", "}", "</", "<div", "if ", "for ", "while ", ";", "=>")
        for (m in markers) if (t.contains(m)) score++
        return score >= 3
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
