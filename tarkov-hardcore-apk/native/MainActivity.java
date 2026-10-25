package hu.taky.tarkovhc;

import android.os.Bundle;

import androidx.activity.OnBackPressedCallback;

import com.getcapacitor.BridgeActivity;

// Vissza gomb: ha nyitva van egy ablak az appban, azt zárja be; különben háttérbe teszi az appot
// (nem lép ki, így a futó raid-időzítő sem vész el).
public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (getBridge() == null || getBridge().getWebView() == null) { moveTaskToBack(true); return; }
                getBridge().getWebView().evaluateJavascript(
                    "(function(){var m=document.getElementById('modal');if(m&&m.classList.contains('on')){m.classList.remove('on');return 'closed';}return 'none';})()",
                    value -> { if (!"\"closed\"".equals(value)) moveTaskToBack(true); });
            }
        });
    }
}
