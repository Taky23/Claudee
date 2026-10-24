package hu.taky.animehub;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.view.View;
import android.widget.RemoteViews;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

// Kezdőképernyős widget: a listád közelgő anime-részeit mutatja.
// Az adatot a webapp írja a Capacitor Preferences-be (SharedPreferences "CapacitorStorage"), itt csak kiolvassuk.
public class AnimeWidget extends AppWidgetProvider {
    @Override
    public void onUpdate(Context ctx, AppWidgetManager mgr, int[] ids) {
        for (int id : ids) render(ctx, mgr, id);
    }

    static void render(Context ctx, AppWidgetManager mgr, int id) {
        RemoteViews v = new RemoteViews(ctx.getPackageName(), R.layout.anime_widget);
        Intent launch = ctx.getPackageManager().getLaunchIntentForPackage(ctx.getPackageName());
        if (launch != null) {
            PendingIntent pi = PendingIntent.getActivity(ctx, 0, launch,
                    PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
            v.setOnClickPendingIntent(R.id.widget_root, pi);
        }
        int[] rows = { R.id.row1, R.id.row2, R.id.row3 };
        int[] times = { R.id.time1, R.id.time2, R.id.time3 };
        for (int r : rows) v.setViewVisibility(r, View.GONE);
        for (int t : times) v.setViewVisibility(t, View.GONE);
        try {
            SharedPreferences sp = ctx.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
            String json = sp.getString("anime_widget", "[]");
            JSONArray arr = new JSONArray(json);
            SimpleDateFormat fmt = new SimpleDateFormat("MM.dd. HH:mm", new Locale("hu"));
            int shown = 0;
            for (int i = 0; i < arr.length() && shown < 3; i++) {
                JSONObject o = arr.getJSONObject(i);
                String title = o.optString("t");
                long at = o.optLong("at");
                int ep = o.optInt("ep");
                v.setViewVisibility(rows[shown], View.VISIBLE);
                v.setViewVisibility(times[shown], View.VISIBLE);
                v.setTextViewText(rows[shown], ep + ". rész · " + title);
                v.setTextViewText(times[shown], fmt.format(new Date(at * 1000)));
                shown++;
            }
            if (shown == 0) {
                v.setViewVisibility(rows[0], View.VISIBLE);
                v.setTextViewText(rows[0], "Nincs közelgő rész a listádon");
            }
        } catch (Exception e) {
            v.setViewVisibility(rows[0], View.VISIBLE);
            v.setTextViewText(rows[0], "Nyisd meg az appot a frissítéshez");
        }
        mgr.updateAppWidget(id, v);
    }
}
