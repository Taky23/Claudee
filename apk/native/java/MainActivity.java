package hu.taky.animehub;

import android.os.Bundle;
import android.webkit.WebView;

import androidx.activity.OnBackPressedCallback;

import com.getcapacitor.BridgeActivity;

// A telefon vissza gombját natívan kezeljük: az appon belül lépünk vissza (a WebView előzményében),
// a legalján pedig NEM lépünk ki, hanem háttérbe tesszük az appot (mint a Home gomb).
public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Később adjuk hozzá, mint a Capacitor sajátját, így ez fut előbb és elkapja a vissza gombot.
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                WebView wv = (getBridge() != null) ? getBridge().getWebView() : null;
                if (wv != null && wv.canGoBack()) {
                    wv.goBack();
                } else {
                    // Ne lépjen ki az appból: csak háttérbe tesszük.
                    moveTaskToBack(true);
                }
            }
        });
    }
}
