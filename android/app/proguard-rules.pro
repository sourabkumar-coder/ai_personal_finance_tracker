# Add project specific ProGuard rules here.
-keep class com.smartfinance.tracker.model.** { *; }
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}
