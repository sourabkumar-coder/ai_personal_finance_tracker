package com.smartfinance.tracker.network

import com.smartfinance.tracker.model.AutoDetectRequest
import com.smartfinance.tracker.model.AutoDetectResponse
import com.smartfinance.tracker.model.SimulateNotificationRequest
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface ApiService {

    @POST("api/transactions/auto-detect")
    suspend fun autoDetect(
        @Body request: AutoDetectRequest
    ): Response<AutoDetectResponse>

    @POST("api/transactions/simulate-notification")
    suspend fun simulateNotification(
        @Body request: SimulateNotificationRequest
    ): Response<AutoDetectResponse>

    @GET("api/transactions/{student_id}/status")
    suspend fun getTrackingStatus(
        @Path("student_id") studentId: Int
    ): Response<Map<String, Any>>
}
