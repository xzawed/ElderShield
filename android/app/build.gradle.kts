import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp") version "2.0.21-1.0.25"
}

val keystorePropertiesFile = rootProject.file("keystore.properties")
val keystoreProperties = Properties()
if (keystorePropertiesFile.exists()) {
    keystorePropertiesFile.inputStream().use { keystoreProperties.load(it) }
}

android {
    namespace = "com.eldershield"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.eldershield"
        minSdk = 29
        targetSdk = 35
        versionCode = 2
        versionName = "0.2.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        // Release Play builds (no device key in APK):
        //   -Peldershield.baseUrl=https://api.example.com
        //   -Peldershield.playCloudProjectNumber=123456789012
        // Or set the same keys in android/local.properties (gitignored).
        fun prop(name: String): String {
            val fromProject = (project.findProperty(name) as String?)?.trim()
            if (!fromProject.isNullOrEmpty()) return fromProject
            val localFile = rootProject.file("local.properties")
            if (localFile.exists()) {
                val p = Properties()
                localFile.inputStream().use { p.load(it) }
                return p.getProperty(name)?.trim().orEmpty()
            }
            return ""
        }
        val baseUrl = prop("eldershield.baseUrl")
        val cloudProject = prop("eldershield.playCloudProjectNumber").ifEmpty { "0" }
        buildConfigField("String", "BASE_URL", "\"${baseUrl.replace("\"", "\\\"")}\"")
        buildConfigField(
            "String",
            "PLAY_CLOUD_PROJECT_NUMBER",
            "\"${cloudProject.replace("\"", "\\\"")}\"",
        )
    }

    buildFeatures {
        buildConfig = true
    }

    signingConfigs {
        if (keystorePropertiesFile.exists()) {
            create("release") {
                keyAlias = keystoreProperties["keyAlias"] as String
                keyPassword = keystoreProperties["keyPassword"] as String
                storeFile = rootProject.file(keystoreProperties["storeFile"] as String)
                storePassword = keystoreProperties["storePassword"] as String
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            if (keystorePropertiesFile.exists()) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(project(":core"))
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")
    implementation("androidx.work:work-runtime-ktx:2.10.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    implementation("com.google.android.play:integrity:1.4.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
}
