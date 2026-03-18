package com.aigor.app

import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.Spinner
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class SettingsActivity : AppCompatActivity() {

    override fun attachBaseContext(newBase: android.content.Context) {
        val prefs = newBase.getSharedPreferences("aigor_prefs", android.content.Context.MODE_PRIVATE)
        val code = prefs.getString("ui_locale", "auto")
        super.attachBaseContext(LocaleManager.apply(newBase, code))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        val endpointEdit: EditText = findViewById(R.id.settingsEndpointEdit)
        val tokenEdit: EditText = findViewById(R.id.settingsTokenEdit)
        val themeSpinner: Spinner = findViewById(R.id.themeSpinner)
        val languageSpinner: Spinner = findViewById(R.id.languageSpinner)
        val showTranscriptionsCheck: CheckBox = findViewById(R.id.showTranscriptionsCheck)
        val saveButton: Button = findViewById(R.id.saveSettingsButton)
        val statusText: TextView = findViewById(R.id.settingsStatusText)

        val prefs = getSharedPreferences("aigor_prefs", MODE_PRIVATE)
        endpointEdit.setText(prefs.getString("openclaw_endpoint", "http://192.168.0.102:8092/chat"))
        tokenEdit.setText(prefs.getString("openclaw_hook_token", ""))

        val themes = ThemeManager.themes
        val labels = themes.map { it.label }
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, labels)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        themeSpinner.adapter = adapter

        val currentThemeId = prefs.getString(ThemeManager.PREF_KEY, "html_match")
        val selectedIndex = themes.indexOfFirst { it.id == currentThemeId }.coerceAtLeast(0)
        themeSpinner.setSelection(selectedIndex)

        // UI language selector (app interface only), easy to extend later.
        val languageOptions = listOf(
            "auto" to getString(R.string.lang_auto),
            "en-GB" to "English (UK)",
            "en-US" to "English (US)",
            "ca-ES" to "Català",
            "es-ES" to "Español",
            "gl-ES" to "Galego",
            "eu-ES" to "Euskara",
        )
        val langAdapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, languageOptions.map { it.second })
        langAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        languageSpinner.adapter = langAdapter

        val currentLang = prefs.getString("ui_locale", "auto") ?: "auto"
        val langIndex = languageOptions.indexOfFirst { it.first == currentLang }.coerceAtLeast(0)
        languageSpinner.setSelection(langIndex)

        showTranscriptionsCheck.isChecked = prefs.getBoolean("show_transcriptions", true)

        saveButton.setOnClickListener {
            val endpoint = endpointEdit.text.toString().trim()
            val token = tokenEdit.text.toString().trim()
            val themeId = themes[themeSpinner.selectedItemPosition].id
            val selectedLang = languageOptions[languageSpinner.selectedItemPosition].first
            val showTranscriptions = showTranscriptionsCheck.isChecked

            if (endpoint.isBlank() || token.isBlank()) {
                statusText.text = "Omple endpoint i token"
                return@setOnClickListener
            }

            prefs.edit()
                .putString("openclaw_endpoint", endpoint)
                .putString("openclaw_hook_token", token)
                .putString(ThemeManager.PREF_KEY, themeId)
                .putString("ui_locale", selectedLang)
                .putBoolean("show_transcriptions", showTranscriptions)
                .apply()

            statusText.text = getString(R.string.saved_ok)
            setResult(RESULT_OK)
            recreate()
        }
    }
}
