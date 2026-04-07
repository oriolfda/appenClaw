package ai.appenclaw.app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.util.AttributeSet
import android.view.View
import kotlin.math.max
import kotlin.math.min

class AudioWaveProgressView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {

    private val heights = intArrayOf(8, 14, 10, 18, 12, 9, 16, 11, 20, 13, 10, 15, 9, 17, 12, 8, 14, 10)
    private var progress: Float = 0f
    private var baseColor: Int = 0xFF7C879A.toInt()
    private var fillColor: Int = 0xFFFF5C5C.toInt()

    private val basePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }

    fun setColors(base: Int, fill: Int) {
        baseColor = base
        fillColor = fill
        invalidate()
    }

    fun setProgress(value: Float) {
        progress = min(1f, max(0f, value))
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat()
        val h = height.toFloat()
        if (w <= 0f || h <= 0f) return

        val barWidth = max(2f, w / 64f)
        val gap = barWidth
        val total = heights.size * barWidth + (heights.size - 1) * gap
        val startX = (w - total) / 2f
        val progressX = startX + total * progress

        basePaint.color = baseColor
        fillPaint.color = fillColor

        var x = startX
        for (i in heights.indices) {
            val bh = min(h, heights[i].toFloat() / 20f * h)
            val top = (h - bh) / 2f
            val right = x + barWidth
            val radius = barWidth / 2f

            canvas.drawRoundRect(x, top, right, top + bh, radius, radius, basePaint)

            val fillRight = min(right, progressX)
            if (fillRight > x) {
                canvas.drawRoundRect(x, top, fillRight, top + bh, radius, radius, fillPaint)
            }
            x = right + gap
        }
    }
}
