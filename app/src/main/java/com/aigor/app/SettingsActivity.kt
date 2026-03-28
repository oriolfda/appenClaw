package com.aigor.app

import android.app.AlertDialog
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.PorterDuff
import android.graphics.drawable.GradientDrawable
import android.widget.LinearLayout
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.CheckBox
import android.widget.EditText
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton

class SettingsActivity : AppCompatActivity() {

    override fun attachBaseContext(newBase: android.content.Context) {
        val prefs = newBase.getSharedPreferences("aigor_prefs", android.content.Context.MODE_PRIVATE)
        val code = prefs.getString("ui_locale", "auto")
        super.attachBaseContext(LocaleManager.apply(newBase, code))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        val root: ScrollView = findViewById(R.id.settingsRoot)
        val content: LinearLayout = root.getChildAt(0) as LinearLayout
        val endpointEdit: EditText = findViewById(R.id.settingsEndpointEdit)
        val tokenEdit: EditText = findViewById(R.id.settingsTokenEdit)
        val themeSpinner: Spinner = findViewById(R.id.themeSpinner)
        val themeSpinnerFake: TextView = findViewById(R.id.themeSpinnerFake)
        val languageSpinner: Spinner = findViewById(R.id.languageSpinner)
        val languageSpinnerFake: TextView = findViewById(R.id.languageSpinnerFake)
        val showTranscriptionsCheck: CheckBox = findViewById(R.id.showTranscriptionsCheck)
        val saveButton: MaterialButton = findViewById(R.id.saveSettingsButton)
        val statusText: TextView = findViewById(R.id.settingsStatusText)

        val prefs = getSharedPreferences("aigor_prefs", MODE_PRIVATE)
        val uiTheme = ThemeManager.byId(prefs.getString(ThemeManager.PREF_KEY, "html_match"))
        val isLight = uiTheme.screenBg > 0xFF7FFFFFFF.toInt()
        val panelBg = if (uiTheme.menuTint != 0) uiTheme.menuTint else uiTheme.screenBg

        window.decorView.setBackgroundColor(uiTheme.screenBg)
        window.statusBarColor = uiTheme.screenBg
        window.navigationBarColor = uiTheme.screenBg
        root.setBackgroundColor(uiTheme.screenBg)
        content.setBackgroundColor(uiTheme.screenBg)
        styleAllTextViews(content, uiTheme.messageTextColor)
        endpointEdit.setTextColor(uiTheme.messageTextColor)
        endpointEdit.setHintTextColor(uiTheme.messageHintColor)
        endpointEdit.setBackgroundResource(uiTheme.inputBg)
        tokenEdit.setTextColor(uiTheme.messageTextColor)
        tokenEdit.setHintTextColor(uiTheme.messageHintColor)
        tokenEdit.setBackgroundResource(uiTheme.inputBg)
        tintSpinner(themeSpinner, panelBg, uiTheme.messageTextColor)
        tintSpinner(languageSpinner, panelBg, uiTheme.messageTextColor)
        themeSpinnerFake.setTextColor(uiTheme.messageTextColor)
        themeSpinnerFake.setBackgroundColor(panelBg)
        languageSpinnerFake.setTextColor(uiTheme.messageTextColor)
        languageSpinnerFake.setBackgroundColor(panelBg)
        themeSpinner.setPopupBackgroundDrawable(GradientDrawable().apply { setColor(panelBg) })
        languageSpinner.setPopupBackgroundDrawable(GradientDrawable().apply { setColor(panelBg) })
        statusText.setTextColor(uiTheme.statusColor)
        showTranscriptionsCheck.setTextColor(uiTheme.messageTextColor)
        showTranscriptionsCheck.buttonTintList = ColorStateList.valueOf(uiTheme.sendTint)

        saveButton.backgroundTintList = ColorStateList.valueOf(uiTheme.sendTint)
        saveButton.setTextColor(uiTheme.sendText)
        saveButton.strokeColor = ColorStateList.valueOf(uiTheme.sendTint)

        endpointEdit.setText(prefs.getString("openclaw_endpoint", "http://192.168.0.102:8092/chat"))
        tokenEdit.setText(prefs.getString("openclaw_hook_token", ""))

        val themes = ThemeManager.themes
        val themeLabels = themes.map { it.label }
        val themeAdapter = themedAdapter(themeLabels, isLight)
        themeSpinner.adapter = themeAdapter

        val currentThemeId = prefs.getString(ThemeManager.PREF_KEY, "html_match")
        val selectedIndex = themes.indexOfFirst { it.id == currentThemeId }.coerceAtLeast(0)
        themeSpinner.setSelection(selectedIndex)
        themeSpinnerFake.text = themeLabels[selectedIndex]
        themeSpinnerFake.setOnClickListener {
            showThemedChoiceDialog(
                title = getString(R.string.settings_theme),
                items = themeLabels,
                selectedIndex = themeSpinner.selectedItemPosition,
                uiTheme = uiTheme,
            ) { index ->
                themeSpinner.setSelection(index)
                themeSpinnerFake.text = themeLabels[index]
            }
        }

        val languageOptions = listOf(
            "auto" to getString(R.string.lang_auto),
            "en-GB" to "English (UK)",
            "en-US" to "English (US)",
            "ca-ES" to "Català",
            "es-ES" to "Español",
            "gl-ES" to "Galego",
            "eu-ES" to "Euskara",
        )
        val langAdapter = themedAdapter(languageOptions.map { it.second }, isLight)
        languageSpinner.adapter = langAdapter

        val currentLang = prefs.getString("ui_locale", "auto") ?: "auto"
        val langIndex = languageOptions.indexOfFirst { it.first == currentLang }.coerceAtLeast(0)
        languageSpinner.setSelection(langIndex)
        languageSpinnerFake.text = languageOptions[langIndex].second
        languageSpinnerFake.setOnClickListener {
            val labels = languageOptions.map { it.second }
            showThemedChoiceDialog(
                title = getString(R.string.settings_ui_language),
                items = labels,
                selectedIndex = languageSpinner.selectedItemPosition,
                uiTheme = uiTheme,
            ) { index ->
                languageSpinner.setSelection(index)
                languageSpinnerFake.text = labels[index]
            }
        }

        showTranscriptionsCheck.isChecked = prefs.getBoolean("show_transcriptions", true)

        saveButton.setOnClickListener {
            val endpoint = endpointEdit.text.toString().trim()
            val token = tokenEdit.text.toString().trim()
            val themeId = themes[themeSpinner.selectedItemPosition].id
            val selectedLang = languageOptions[languageSpinner.selectedItemPosition].first
            val showTranscriptions = showTranscriptionsCheck.isChecked

            if (endpoint.isBlank() || token.isBlank()) {
                statusText.text = getString(R.string.fill_endpoint_token)
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

    private fun themedAdapter(items: List<String>, isLight: Boolean): ArrayAdapter<String> {
        val textColor = if (isLight) Color.parseColor("#0F172A") else Color.parseColor("#F3F4F6")
        val bgColor = if (isLight) Color.parseColor("#F8FAFC") else Color.parseColor("#111827")

        return object : ArrayAdapter<String>(this, android.R.layout.simple_spinner_item, items) {
            override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
                val v = super.getView(position, convertView, parent)
                (v as? TextView)?.apply {
                    setTextColor(textColor)
                    setBackgroundColor(bgColor)
                }
                return v
            }

            override fun getDropDownView(position: Int, convertView: View?, parent: ViewGroup): View {
                val v = super.getDropDownView(position, convertView, parent)
                (v as? TextView)?.apply {
                    setTextColor(textColor)
                    setBackgroundColor(bgColor)
                }
                return v
            }
        }.also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
    }

    private fun showThemedChoiceDialog(
        title: String,
        items: List<String>,
        selectedIndex: Int,
        uiTheme: ThemeManager.UiTheme,
        onSelected: (Int) -> Unit,
    ) {
        val adapter = object : ArrayAdapter<String>(this, android.R.layout.simple_list_item_single_choice, items) {
            override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
                val view = super.getView(position, convertView, parent)
                val checked = view.findViewById<android.widget.CheckedTextView>(android.R.id.text1)
                checked.setTextColor(uiTheme.messageTextColor)
                checked.checkMarkTintList = ColorStateList.valueOf(uiTheme.sendTint)
                view.setBackgroundColor(uiTheme.dialogBg)
                return view
            }
        }

        val dialog = AlertDialog.Builder(this)
            .setTitle(title)
            .setSingleChoiceItems(adapter, selectedIndex) { d, which ->
                onSelected(which)
                d.dismiss()
            }
            .setNegativeButton(getString(R.string.close), null)
            .create()

        dialog.setOnShowListener {
            dialog.window?.decorView?.setBackgroundColor(uiTheme.dialogBg)
            dialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(uiTheme.menuDotsColor)
            val titleViewId = resources.getIdentifier("alertTitle", "id", "android")
            dialog.findViewById<TextView?>(titleViewId)?.setTextColor(uiTheme.titleColor)
            dialog.findViewById<TextView?>(android.R.id.message)?.setTextColor(uiTheme.messageTextColor)
            dialog.listView?.setBackgroundColor(uiTheme.dialogBg)
            dialog.listView?.dividerHeight = 0
        }
        dialog.show()
    }

    private fun styleAllTextViews(root: View, color: Int) {
        if (root is TextView) root.setTextColor(color)
        if (root is ViewGroup) {
            for (i in 0 until root.childCount) {
                styleAllTextViews(root.getChildAt(i), color)
            }
        }
    }

    private fun tintSpinner(spinner: Spinner, backgroundColor: Int, textColor: Int) {
        spinner.background = GradientDrawable().apply {
            cornerRadius = 18f
            setColor(backgroundColor)
        }
        spinner.background?.mutate()?.setColorFilter(backgroundColor, PorterDuff.Mode.SRC_ATOP)
        spinner.backgroundTintList = ColorStateList.valueOf(backgroundColor)
        spinner.foregroundTintList = ColorStateList.valueOf(textColor)
    }
}
