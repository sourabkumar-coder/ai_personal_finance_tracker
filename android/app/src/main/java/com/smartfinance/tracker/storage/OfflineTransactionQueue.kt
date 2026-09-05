package com.smartfinance.tracker.storage

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.smartfinance.tracker.model.AutoDetectRequest

/**
 * Offline transaction queue: buffers notifications when offline or when
 * the backend API is unreachable, then replays them once connected.
 */
class OfflineTransactionQueue(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_QUEUE, Context.MODE_PRIVATE)
    private val gson = Gson()

    @Synchronized
    fun enqueue(request: AutoDetectRequest) {
        val list = getAll().toMutableList()
        // Limit queue to 50 entries to preserve storage
        if (list.size >= 50) {
            list.removeAt(0)
        }
        list.add(request)
        saveList(list)
    }

    @Synchronized
    fun peekAll(): List<AutoDetectRequest> {
        return getAll()
    }

    @Synchronized
    fun remove(request: AutoDetectRequest) {
        val list = getAll().toMutableList()
        list.remove(request)
        saveList(list)
    }

    @Synchronized
    fun clear() {
        prefs.edit().remove(KEY_QUEUE_ITEMS).apply()
    }

    private fun getAll(): List<AutoDetectRequest> {
        val json = prefs.getString(KEY_QUEUE_ITEMS, null) ?: return emptyList()
        return try {
            val type = object : TypeToken<List<AutoDetectRequest>>() {}.type
            gson.fromJson(json, type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    private fun saveList(list: List<AutoDetectRequest>) {
        val json = gson.toJson(list)
        prefs.edit().putString(KEY_QUEUE_ITEMS, json).apply()
    }

    companion object {
        private const val PREFS_QUEUE = "offline_transaction_queue"
        private const val KEY_QUEUE_ITEMS = "pending_auto_detect_items"
    }
}
