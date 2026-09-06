package com.qrew.app;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationManager;
import android.os.SystemClock;

import androidx.core.content.ContextCompat;
import androidx.core.location.LocationCompat;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.util.List;

/**
 * Reports whether the fixes the operating system is currently handing out are
 * simulated. Android marks every Location with that flag, but the Capacitor
 * geolocation plugin drops it, so the app reads it here and forwards it to the
 * gate. The verdict is only ever a claim made by the handset: it is the device
 * attestation that makes the claim worth anything.
 */
@CapacitorPlugin(name = "LocationIntegrity")
public class LocationIntegrityPlugin extends Plugin {

    /** A fix older than this says nothing about the position just reported. */
    private static final long MAX_FIX_AGE_NANOS = 120L * 1_000_000_000L;

    private static final String STATUS_MOCK = "mock";
    private static final String STATUS_CLEAN = "clean";
    private static final String STATUS_UNKNOWN = "unknown";

    @PluginMethod
    public void check(PluginCall call) {
        JSObject result = new JSObject();
        result.put("status", readStatus());
        call.resolve(result);
    }

    /** Answers unknown whenever the platform cannot be asked, never mock. */
    private String readStatus() {
        Context context = getContext();
        if (context == null || !hasLocationPermission(context)) {
            return STATUS_UNKNOWN;
        }
        LocationManager manager = (LocationManager) context.getSystemService(Context.LOCATION_SERVICE);
        if (manager == null) {
            return STATUS_UNKNOWN;
        }
        List<String> providers = manager.getProviders(true);
        if (providers == null || providers.isEmpty()) {
            return STATUS_UNKNOWN;
        }
        long now = SystemClock.elapsedRealtimeNanos();
        boolean sawFix = false;
        for (String provider : providers) {
            Location location;
            try {
                location = manager.getLastKnownLocation(provider);
            } catch (SecurityException | IllegalArgumentException exception) {
                continue;
            }
            if (location == null || now - location.getElapsedRealtimeNanos() > MAX_FIX_AGE_NANOS) {
                continue;
            }
            sawFix = true;
            if (LocationCompat.isMock(location)) {
                return STATUS_MOCK;
            }
        }
        return sawFix ? STATUS_CLEAN : STATUS_UNKNOWN;
    }

    private boolean hasLocationPermission(Context context) {
        return ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
                == PackageManager.PERMISSION_GRANTED
                || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
    }
}
