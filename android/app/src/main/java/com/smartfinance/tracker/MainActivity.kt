package com.smartfinance.tracker

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.NotificationManagerCompat
import androidx.lifecycle.lifecycleScope
import com.smartfinance.tracker.databinding.ActivityMainBinding
import com.smartfinance.tracker.model.SimulateNotificationRequest
import com.smartfinance.tracker.network.ApiClient
import com.smartfinance.tracker.service.TransactionNotificationListener
import com.smartfinance.tracker.storage.AppPreferences
import com.smartfinance.tracker.ui.OnboardingActivity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var prefs: AppPreferences

    private val transactionReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == TransactionNotificationListener.ACTION_TRANSACTION_DETECTED) {
                val merchant = intent.getStringExtra(TransactionNotificationListener.EXTRA_MERCHANT) ?: "Unknown"
                val amount = intent.getDoubleExtra(TransactionNotificationListener.EXTRA_AMOUNT, 0.0)
                val category = intent.getStringExtra(TransactionNotificationListener.EXTRA_CATEGORY) ?: "Auto"
                val source = intent.getStringExtra(TransactionNotificationListener.EXTRA_SOURCE) ?: "UPI"

                val timeStr = SimpleDateFormat("hh:mm a, dd MMM", Locale.getDefault()).format(Date())
                val summaryText = "⚡ ₹$amount at $merchant\nCategory: $category • $source\nDetected at $timeStr"
                binding.tvLastDetected.text = summaryText
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        prefs = AppPreferences(this)

        setupListeners()
        updateServerInfo()
    }

    override fun onResume() {
        super.onResume()
        checkPermissionStatus()
        loadLastDetected()

        val filter = IntentFilter(TransactionNotificationListener.ACTION_TRANSACTION_DETECTED)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(transactionReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(transactionReceiver, filter)
        }
    }

    override fun onPause() {
        super.onPause()
        try {
            unregisterReceiver(transactionReceiver)
        } catch (_: Exception) {}
    }

    private fun checkPermissionStatus() {
        val hasAccess = isNotificationServiceEnabled()
        if (hasAccess) {
            binding.tvStatusTitle.text = getString(R.string.status_active)
            binding.tvStatusTitle.setTextColor(getColor(R.color.accent_green))
            binding.tvStatusDesc.text = getString(R.string.status_desc_active)
            binding.btnPermission.text = "Permission Granted (Active)"
            binding.btnPermission.isEnabled = false
            binding.btnPermission.alpha = 0.6f
        } else {
            binding.tvStatusTitle.text = getString(R.string.status_inactive)
            binding.tvStatusTitle.setTextColor(getColor(R.color.accent_amber))
            binding.tvStatusDesc.text = getString(R.string.status_desc_inactive)
            binding.btnPermission.text = getString(R.string.btn_grant_permission)
            binding.btnPermission.isEnabled = true
            binding.btnPermission.alpha = 1.0f
        }
    }

    private fun isNotificationServiceEnabled(): Boolean {
        val enabledPackages = NotificationManagerCompat.getEnabledListenerPackages(this)
        return enabledPackages.contains(packageName)
    }

    private fun setupListeners() {
        binding.btnPermission.setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }

        binding.btnOnboardingLink.setOnClickListener {
            startActivity(Intent(this, OnboardingActivity::class.java))
        }

        binding.btnSimulate.setOnClickListener {
            simulateSamplePayment()
        }

        binding.btnSettings.setOnClickListener {
            showSettingsDialog()
        }
    }

    private fun simulateSamplePayment() {
        val samples = listOf(
            "Paid ₹180 to Chai Point using UPI" to "Google Pay",
            "Paid ₹450 to Swiggy using UPI" to "PhonePe",
            "Paid ₹1,200 to Amazon Pay India" to "Paytm",
            "Paid ₹85 to Metro Smart Card Recharge" to "BHIM"
        )
        val randomSample = samples.random()

        binding.btnSimulate.isEnabled = false
        lifecycleScope.launch {
            try {
                val service = ApiClient.getService(this@MainActivity)
                val response = withContext(Dispatchers.IO) {
                    service.simulateNotification(
                        SimulateNotificationRequest(
                            studentId = prefs.studentId,
                            text = randomSample.first,
                            sourceApp = randomSample.second
                        )
                    )
                }

                if (response.isSuccessful && response.body()?.success == true) {
                    val body = response.body()!!
                    val summaryText = "⚡ ₹${body.amount} at ${body.merchant}\nCategory: ${body.category} • ${randomSample.second}\nLogged instantly to Web Dashboard!"
                    binding.tvLastDetected.text = summaryText
                    prefs.lastDetectedSummary = summaryText
                    prefs.lastDetectedTimestamp = System.currentTimeMillis()

                    Toast.makeText(
                        this@MainActivity,
                        "Simulated: ₹${body.amount} at ${body.merchant} (${body.category})",
                        Toast.LENGTH_LONG
                    ).show()
                } else {
                    Toast.makeText(
                        this@MainActivity,
                        "Failed: ${response.message()}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            } catch (e: Exception) {
                Toast.makeText(
                    this@MainActivity,
                    "Connection error: ${e.message}",
                    Toast.LENGTH_LONG
                ).show()
            } finally {
                binding.btnSimulate.isEnabled = true
            }
        }
    }

    private fun showSettingsDialog() {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(50, 30, 50, 10)
        }

        val urlInput = EditText(this).apply {
            hint = "http://10.0.2.2:8000/ or LAN IP"
            setText(prefs.backendBaseUrl)
        }
        val idInput = EditText(this).apply {
            hint = "Student ID (e.g. 1)"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
            setText(prefs.studentId.toString())
        }

        layout.addView(urlInput)
        layout.addView(idInput)

        AlertDialog.Builder(this)
            .setTitle(R.string.dialog_settings_title)
            .setMessage("Set your FastAPI backend address and Student ID for multi-device sync.")
            .setView(layout)
            .setPositiveButton(R.string.btn_save) { _, _ ->
                val newUrl = urlInput.text.toString().trim()
                val newId = idInput.text.toString().trim().toIntOrNull() ?: 1

                if (newUrl.isNotBlank()) {
                    prefs.backendBaseUrl = newUrl
                    prefs.studentId = newId
                    ApiClient.reset()
                    updateServerInfo()
                    Toast.makeText(this, "Settings updated", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton(R.string.btn_cancel, null)
            .show()
    }

    private fun updateServerInfo() {
        binding.tvServerInfo.text = "Connected to: ${prefs.backendBaseUrl} (Student #${prefs.studentId})"
    }

    private fun loadLastDetected() {
        val summary = prefs.lastDetectedSummary
        if (!summary.isNullOrBlank()) {
            binding.tvLastDetected.text = summary
        }
    }
}
