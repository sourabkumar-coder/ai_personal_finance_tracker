package com.smartfinance.tracker.service

import android.app.Notification
import android.content.Intent
import android.os.Build
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.smartfinance.tracker.model.AutoDetectRequest
import com.smartfinance.tracker.network.ApiClient
import com.smartfinance.tracker.parser.TransactionParser
import com.smartfinance.tracker.storage.AppPreferences
import com.smartfinance.tracker.storage.OfflineTransactionQueue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class TransactionNotificationListener : NotificationListenerService() {

    private val job = SupervisorJob()
    private val scope = CoroutineScope(Dispatchers.IO + job)
    private lateinit var prefs: AppPreferences
    private lateinit var queue: OfflineTransactionQueue

    override fun onCreate() {
        super.onCreate()
        prefs = AppPreferences(applicationContext)
        queue = OfflineTransactionQueue(applicationContext)
        Log.i(TAG, "SmartFinance TransactionNotificationListener created.")
    }

    override fun onDestroy() {
        super.onDestroy()
        job.cancel()
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        Log.i(TAG, "NotificationListener connected and active.")
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        super.onNotificationPosted(sbn)
        if (sbn == null) return

        val packageName = sbn.packageName ?: return

        // 1. Check if user has enabled auto-detection
        if (!prefs.isAutoDetectionEnabled) {
            return
        }

        // 2. Filter for supported UPI/Banking apps
        if (!TransactionParser.isSupportedApp(packageName)) {
            return
        }

        // 3. Extract text from notification extras
        val extras = sbn.notification?.extras ?: return
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString() ?: ""
        var text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""
        val bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()
        if (!bigText.isNullOrBlank() && bigText.length > text.length) {
            text = bigText
        }

        val subText = extras.getCharSequence(Notification.EXTRA_SUB_TEXT)?.toString() ?: ""
        val combinedText = "$title $text $subText".trim()

        Log.d(TAG, "Received notification from $packageName: $combinedText")

        // 4. Parse transaction details on device
        val parsed = TransactionParser.parse(title, text, packageName)
        if (!parsed.isFinancial || !parsed.isSuccess || parsed.amount == null) {
            Log.d(TAG, "Filtered non-financial or failed notification: $combinedText")
            return
        }

        // 5. Build request payload
        val isoTimestamp = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault()).format(Date())
        val request = AutoDetectRequest(
            studentId = prefs.studentId,
            notificationText = parsed.rawText,
            sourceApp = parsed.sourceApp,
            merchant = parsed.merchant,
            amount = parsed.amount,
            transactionType = parsed.transactionType,
            currency = "INR",
            referenceId = parsed.referenceId,
            transactionTimestamp = isoTimestamp
        )

        // 6. Post to backend or queue offline
        scope.launch {
            sendTransaction(request)
        }
    }

    private suspend fun sendTransaction(request: AutoDetectRequest) {
        try {
            val service = ApiClient.getService(applicationContext)
            val response = service.autoDetect(request)

            if (response.isSuccessful && response.body()?.success == true) {
                val body = response.body()!!
                Log.i(TAG, "Successfully auto-detected transaction: ${body.merchant} - ₹${body.amount}")

                val summary = "${body.merchant ?: request.merchant} - ₹${body.amount ?: request.amount} (${body.category ?: "Auto"})"
                prefs.lastDetectedSummary = summary
                prefs.lastDetectedTimestamp = System.currentTimeMillis()

                // Broadcast update for active UI
                val intent = Intent(ACTION_TRANSACTION_DETECTED).apply {
                    setPackage(packageName)
                    putExtra(EXTRA_MERCHANT, body.merchant ?: request.merchant)
                    putExtra(EXTRA_AMOUNT, body.amount ?: request.amount)
                    putExtra(EXTRA_CATEGORY, body.category ?: "Expense")
                    putExtra(EXTRA_SOURCE, request.sourceApp)
                }
                sendBroadcast(intent)

                // Flush any offline queued transactions
                flushOfflineQueue()
            } else {
                Log.w(TAG, "Server returned error: ${response.code()} ${response.errorBody()?.string()}")
                queue.enqueue(request)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to connect to backend, queueing offline: ${e.message}")
            queue.enqueue(request)
        }
    }

    private suspend fun flushOfflineQueue() {
        val pending = queue.peekAll()
        if (pending.isEmpty()) return

        Log.i(TAG, "Flushing ${pending.size} offline transactions...")
        val service = ApiClient.getService(applicationContext)

        for (item in pending) {
            try {
                val response = service.autoDetect(item)
                if (response.isSuccessful && response.body()?.success == true) {
                    queue.remove(item)
                }
            } catch (e: Exception) {
                Log.w(TAG, "Offline flush retry failed for item: ${e.message}")
                break
            }
        }
    }

    companion object {
        private const val TAG = "TxNotificationListener"
        const val ACTION_TRANSACTION_DETECTED = "com.smartfinance.tracker.TRANSACTION_DETECTED"
        const val EXTRA_MERCHANT = "extra_merchant"
        const val EXTRA_AMOUNT = "extra_amount"
        const val EXTRA_CATEGORY = "extra_category"
        const val EXTRA_SOURCE = "extra_source"
    }
}
