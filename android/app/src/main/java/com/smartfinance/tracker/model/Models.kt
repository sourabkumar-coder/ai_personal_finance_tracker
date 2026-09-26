package com.smartfinance.tracker.model

import com.google.gson.annotations.SerializedName

/**
 * Payload sent to POST /api/transactions/auto-detect
 */
data class AutoDetectRequest(
    @SerializedName("student_id")
    val studentId: Int,

    @SerializedName("notification_text")
    val notificationText: String? = null,

    @SerializedName("source_app")
    val sourceApp: String? = null,

    @SerializedName("merchant")
    val merchant: String? = null,

    @SerializedName("amount")
    val amount: Double? = null,

    @SerializedName("transaction_type")
    val transactionType: String? = "EXPENSE",

    @SerializedName("currency")
    val currency: String? = "INR",

    @SerializedName("reference_id")
    val referenceId: String? = null,

    @SerializedName("transaction_timestamp")
    val transactionTimestamp: String? = null
)

/**
 * Response received from POST /api/transactions/auto-detect
 */
data class AutoDetectResponse(
    @SerializedName("success")
    val success: Boolean,

    @SerializedName("message")
    val message: String,

    @SerializedName("action")
    val action: String,

    @SerializedName("expense_id")
    val expenseId: Int? = null,

    @SerializedName("merchant")
    val merchant: String? = null,

    @SerializedName("amount")
    val amount: Double? = null,

    @SerializedName("category")
    val category: String? = null,

    @SerializedName("transaction_type")
    val transactionType: String? = null,

    @SerializedName("confidence")
    val confidence: Double? = null,

    @SerializedName("is_duplicate")
    val isDuplicate: Boolean? = false,

    @SerializedName("detected_at")
    val detectedAt: String? = null
)

/**
 * Simulation request payload
 */
data class SimulateNotificationRequest(
    @SerializedName("student_id")
    val studentId: Int,

    @SerializedName("notification_text")
    val text: String,

    @SerializedName("source_app")
    val sourceApp: String = "Google Pay"
)

/**
 * Local parsed representation of an incoming status bar notification
 */
data class ParsedNotification(
    val isFinancial: Boolean,
    val amount: Double?,
    val merchant: String?,
    val transactionType: String,
    val isSuccess: Boolean,
    val referenceId: String?,
    val rawText: String,
    val sourceApp: String
)
