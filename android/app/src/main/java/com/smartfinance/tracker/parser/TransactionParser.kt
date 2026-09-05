package com.smartfinance.tracker.parser

import com.smartfinance.tracker.model.ParsedNotification
import java.util.regex.Pattern

object TransactionParser {

    private val APP_PACKAGE_MAP = mapOf(
        "com.google.android.apps.nbu.paisa.user" to "Google Pay",
        "com.phonepe.app" to "PhonePe",
        "net.one97.paytm" to "Paytm",
        "in.org.npci.upiapp" to "BHIM",
        "com.csam.icici.bank.imobile" to "ICICI Bank",
        "com.hdfcbank.android" to "HDFC Bank",
        "com.sbi.lotusintouch" to "SBI",
        "com.axis.mobile" to "Axis Bank",
        "com.kotak.mbanking" to "Kotak Bank",
        "com.bankofbaroda.mconnect" to "Bank of Baroda",
        "com.freecharge.android" to "FreeCharge",
        "com.mobikwik_new" to "MobiKwik",
        "com.cred.app" to "CRED"
    )

    private val FINANCIAL_KEYWORDS = listOf(
        "paid", "debited", "sent", "transferred", "spent", "spent at",
        "payment of", "received", "credited", "txn", "upi", "vpa",
        "inr", "rs.", "rs ", "₹"
    )

    private val BLACKLIST_PATTERNS = listOf(
        Pattern.compile("\\b(?:otp|one time password|verification code|secret code)\\b", Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\b(?:available balance|avl bal|bal(?:ance)? is|acct bal|account balance)\\b", Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\b(?:cashback offer|flat \\d+|win up to|discount coupon|rewards points)\\b", Pattern.CASE_INSENSITIVE)
    )

    private val AMOUNT_PATTERNS = listOf(
        Pattern.compile("(?:₹|rs\\.?|inr)\\s*([0-9]+(?:,[0-9]+)*(?:\\.[0-9]{1,2})?)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("([0-9]+(?:,[0-9]+)*(?:\\.[0-9]{1,2})?)\\s*(?:inr|rs\\.?)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\b(?:paid|sent|debited|spent|transferred|credited|received)\\s*(?:₹|rs\\.?|inr)?\\s*([0-9]+(?:,[0-9]+)*(?:\\.[0-9]{1,2})?)", Pattern.CASE_INSENSITIVE)
    )

    private val MERCHANT_PATTERNS = listOf(
        Pattern.compile("(?:paid\\s+(?:to|at)|sent\\s+to|transferred\\s+to|spent\\s+at)\\s+([a-zA-Z0-9&\\.\\s\\-_]+?)(?=(?:\\s+(?:successful|success|using|from|on|via|ref|utr|avail|avl|acct|acc|bal|for)|[\\.,;]|$))", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:received\\s+from|credited\\s+by)\\s+([a-zA-Z0-9&\\.\\s\\-_]+?)(?=(?:\\s+(?:successful|success|using|into|in|on|via|ref|utr|avail|avl|acct|acc|bal)|[\\.,;]|$))", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:at|to)\\s+([A-Za-z0-9&\\.\\-_]+(?:\\s+[A-Za-z0-9&\\.\\-_]+){0,3})\\s+(?:successful|success|via)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("VPA\\s+([a-zA-Z0-9\\.\\-_@]+)", Pattern.CASE_INSENSITIVE)
    )

    private val UTR_PATTERNS = listOf(
        Pattern.compile("(?:UPI\\s+Ref(?:erence)?(?:\\s+No)?|UTR(?:\\s+No)?|Ref(?:\\s+No)?)\\s*[:\\-]?\\s*([0-9]{6,16})", Pattern.CASE_INSENSITIVE)
    )

    fun getSourceAppName(packageName: String): String {
        return APP_PACKAGE_MAP[packageName] ?: "UPI Payment"
    }

    fun isSupportedApp(packageName: String): Boolean {
        return APP_PACKAGE_MAP.containsKey(packageName)
    }

    fun parse(title: String, text: String, packageName: String): ParsedNotification {
        val fullText = "$title $text".trim()
        val sourceApp = getSourceAppName(packageName)

        // 1. Check blacklists (OTP, balance inquiry, promo)
        for (pattern in BLACKLIST_PATTERNS) {
            if (pattern.matcher(fullText).find()) {
                return ParsedNotification(
                    isFinancial = false,
                    amount = null,
                    merchant = null,
                    transactionType = "EXPENSE",
                    isSuccess = false,
                    referenceId = null,
                    rawText = fullText,
                    sourceApp = sourceApp
                )
            }
        }

        // 2. Check financial signal
        val lower = fullText.lowercase()
        val hasSignal = FINANCIAL_KEYWORDS.any { lower.contains(it) }
        if (!hasSignal) {
            return ParsedNotification(
                isFinancial = false,
                amount = null,
                merchant = null,
                transactionType = "EXPENSE",
                isSuccess = false,
                referenceId = null,
                rawText = fullText,
                sourceApp = sourceApp
            )
        }

        // 3. Amount extraction
        var amount: Double? = null
        for (pattern in AMOUNT_PATTERNS) {
            val matcher = pattern.matcher(fullText)
            if (matcher.find()) {
                val rawAmountStr = matcher.group(1)?.replace(",", "")
                try {
                    val parsed = rawAmountStr?.toDouble()
                    if (parsed != null && parsed > 0) {
                        amount = parsed
                        break
                    }
                } catch (_: Exception) {
                }
            }
        }

        // 4. Merchant extraction
        var merchant: String? = null
        for (pattern in MERCHANT_PATTERNS) {
            val matcher = pattern.matcher(fullText)
            if (matcher.find()) {
                val extracted = matcher.group(1)?.trim()
                if (!extracted.isNullOrBlank() && extracted.length > 1) {
                    merchant = cleanMerchant(extracted)
                    break
                }
            }
        }
        if (merchant.isNullOrBlank()) {
            merchant = "$sourceApp Merchant"
        }

        // 5. Transaction type (EXPENSE vs INCOME)
        val isIncome = lower.contains("received") || lower.contains("credited")
        val transactionType = if (isIncome) "INCOME" else "EXPENSE"

        // 6. Status check
        val isFailed = lower.contains("failed") || lower.contains("declined") || lower.contains("cancelled")

        // 7. Reference ID
        var referenceId: String? = null
        for (pattern in UTR_PATTERNS) {
            val matcher = pattern.matcher(fullText)
            if (matcher.find()) {
                referenceId = matcher.group(1)
                break
            }
        }

        return ParsedNotification(
            isFinancial = amount != null && !isFailed,
            amount = amount,
            merchant = merchant,
            transactionType = transactionType,
            isSuccess = !isFailed,
            referenceId = referenceId,
            rawText = fullText,
            sourceApp = sourceApp
        )
    }

    private fun cleanMerchant(raw: String): String {
        var clean = raw.trim()
        clean = clean.replace(Regex("(?i)^(to|at|from|paid to)\\s+"), "")
        clean = clean.replace(Regex("[\\.,;:\\-_]+$"), "")
        return clean.trim().split(" ").joinToString(" ") { word ->
            if (word.length <= 3 && word == word.uppercase()) word
            else word.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
        }
    }
}
