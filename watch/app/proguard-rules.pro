# Keep kotlinx.serialization generated serializers for our DTOs.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**

-keepclassmembers class com.guardian.watch.data.remote.dto.** {
    *** Companion;
}
-keepclasseswithmembers class com.guardian.watch.data.remote.dto.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# Retrofit / OkHttp
-dontwarn okhttp3.**
-dontwarn retrofit2.**
-dontwarn okio.**
