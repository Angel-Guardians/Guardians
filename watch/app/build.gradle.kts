plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.guardian.watch"
    // compileSdk 36 is required by androidx.health.connect 1.1.0; targetSdk (below)
    // stays lower so runtime behavior is unchanged.
    compileSdk = 36

    defaultConfig {
        applicationId = "com.guardian.watch"
        // Wear OS 3 = API 30 (Galaxy Watch 4/5). Wear OS 4/5 = API 33/34 (Watch 6/7).
        minSdk = 30
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"

        // Optional compile-time default for the backend URL (set guardian.baseUrl in
        // gradle.properties or local.properties). Empty => configure on the watch.
        val defaultBaseUrl = (project.findProperty("guardian.baseUrl") as String?).orEmpty()
        buildConfigField("String", "GUARDIAN_DEFAULT_BASE_URL", "\"$defaultBaseUrl\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)

    val composeBom = platform(libs.androidx.compose.bom)
    implementation(composeBom)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.foundation)
    implementation(libs.androidx.compose.ui.tooling.preview)
    debugImplementation(libs.androidx.compose.ui.tooling)

    // Wear OS Compose UI
    implementation(libs.androidx.wear.compose.material)
    implementation(libs.androidx.wear.compose.foundation)

    // Health sensors (heart rate, steps, calories)
    implementation(libs.androidx.health.services)
    // Health Connect (optional): supplemental reads of metrics the device's health
    // app already recorded (SpO2, resting HR, HRV, sleep). No-ops where unavailable.
    implementation(libs.androidx.health.connect)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.coroutines.guava) // ListenableFuture.await()

    // Offline storage
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    // Settings persistence
    implementation(libs.androidx.datastore.preferences)

    // Background sync backstop
    implementation(libs.androidx.work.runtime.ktx)

    // Networking
    implementation(libs.retrofit)
    implementation(libs.retrofit.serialization)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.kotlinx.serialization.json)
}
