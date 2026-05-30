package com.guardian.watch

import android.app.Application
import android.content.Context
import com.guardian.watch.di.GuardianGraph
import com.guardian.watch.sync.SyncWorker

class GuardianWatchApp : Application() {

    lateinit var graph: GuardianGraph
        private set

    override fun onCreate() {
        super.onCreate()
        graph = GuardianGraph(this)
        // Backstop: flush any backlog every ~15 min even if the foreground
        // service isn't running (WorkManager's minimum periodic interval).
        SyncWorker.enqueuePeriodic(this)
    }
}

/** Convenience accessor for the app-wide dependency graph. */
val Context.graph: GuardianGraph
    get() = (applicationContext as GuardianWatchApp).graph
