package com.smartfinance.tracker.network

import android.content.Context
import com.smartfinance.tracker.storage.AppPreferences
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {

    private var currentBaseUrl: String? = null
    private var cachedService: ApiService? = null

    @Synchronized
    fun getService(context: Context): ApiService {
        val prefs = AppPreferences(context)
        val baseUrl = prefs.backendBaseUrl

        if (cachedService != null && currentBaseUrl == baseUrl) {
            return cachedService!!
        }

        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        val okHttpClient = OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        currentBaseUrl = baseUrl
        cachedService = retrofit.create(ApiService::class.java)
        return cachedService!!
    }

    @Synchronized
    fun reset() {
        currentBaseUrl = null
        cachedService = null
    }
}
