package com.guardian.watch.di

import android.content.Context
import com.guardian.watch.data.local.GuardianDatabase
import com.guardian.watch.data.repository.VitalsRepository
import com.guardian.watch.data.settings.SettingsStore
import com.guardian.watch.health.HealthConnectManager
import com.guardian.watch.health.HealthServicesManager
import com.guardian.watch.location.LocationProvider

/**
 * Tiny manual dependency graph — no DI framework. Created once in
 * [com.guardian.watch.GuardianWatchApp] and reached from anywhere via the
 * `Context.graph` extension.
 */
class GuardianGraph(context: Context) {
    private val appContext = context.applicationContext

    val database: GuardianDatabase = GuardianDatabase.getInstance(appContext)
    val settings: SettingsStore = SettingsStore(appContext)
    val repository: VitalsRepository =
        VitalsRepository(database.vitalReadingDao(), database.locationReadingDao(), settings)
    val healthServicesManager: HealthServicesManager = HealthServicesManager(appContext)
    val healthConnectManager: HealthConnectManager = HealthConnectManager(appContext)
    val locationProvider: LocationProvider = LocationProvider(appContext)
}
