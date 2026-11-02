package com.cryptoaitrader.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.URI
import java.util.concurrent.TimeUnit

private val Navy = Color(0xFF0B1220)
private val Panel = Color(0xFF141F32)
private val Mint = Color(0xFF29D3A2)
private val SoftText = Color(0xFF9BAAC0)
private val Http = OkHttpClient.Builder()
    .connectTimeout(12, TimeUnit.SECONDS)
    .readTimeout(18, TimeUnit.SECONDS)
    .writeTimeout(12, TimeUnit.SECONDS)
    .build()

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme(
                primary = Mint,
                background = Navy,
                surface = Panel,
                onBackground = Color(0xFFF1F5F9),
                onSurface = Color(0xFFF1F5F9)
            )) {
                Surface(Modifier.fillMaxSize(), color = Navy) { TraderScreen() }
            }
        }
    }
}

private data class Dashboard(
    val state: String,
    val dryRun: Boolean,
    val exchange: String,
    val timeframe: String,
    val strategy: String,
    val stakeCurrency: String,
    val openTrades: Int,
    val maxOpenTrades: Int,
    val profit: Double,
    val profitPct: Double,
    val wallet: Double,
    val positions: List<String>,
    val version: String
)

private suspend fun apiRequest(baseUrl: String, token: String, path: String, post: Boolean = false): JSONObject {
    return withContext(Dispatchers.IO) {
        val uri = try { URI(baseUrl.trim().trimEnd('/')) } catch (_: Exception) { null }
        if (uri == null || uri.host.isNullOrBlank()) throw IOException("Ingresá una URL válida")
        if (uri.scheme != "https") throw IOException("Por seguridad, el servidor debe usar HTTPS")
        if ((uri.rawPath?.isNotEmpty() == true && uri.rawPath != "/") || uri.rawQuery != null || uri.fragment != null || uri.userInfo != null) {
            throw IOException("Ingresá solo el dominio HTTPS, sin rutas ni parámetros")
        }
        if (token.length < 32) throw IOException("El token debe tener al menos 32 caracteres")
        val builder = Request.Builder()
            .url(baseUrl.trim().trimEnd('/') + path)
            .header("Authorization", "Bearer $token")
            .header("Accept", "application/json")
        if (post) builder.post(ByteArray(0).toRequestBody(null)) else builder.get()
        Http.newCall(builder.build()).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                val detail = try { JSONObject(body).optString("detail") } catch (_: Exception) { "" }
                throw IOException(if (detail.isNotBlank()) detail else "Error HTTP ${response.code}")
            }
            try { JSONObject(body) } catch (_: Exception) { throw IOException("El servidor devolvió una respuesta inválida") }
        }
    }
}

private fun parseDashboard(root: JSONObject): Dashboard {
    val bot = root.optJSONObject("bot") ?: JSONObject()
    val profit = root.optJSONObject("profit") ?: JSONObject()
    val count = root.optJSONObject("count") ?: JSONObject()
    val balance = root.optJSONObject("balance") ?: JSONObject()
    val positions = mutableListOf<String>()
    val open = root.optJSONArray("open_trades") ?: JSONArray()
    for (i in 0 until open.length()) {
        val trade = open.optJSONObject(i) ?: continue
        val pair = trade.optString("pair", "Par")
        val amount = trade.optDouble("amount", 0.0)
        val rate = trade.optDouble("open_rate", 0.0)
        val pnl = trade.optDouble("profit_pct", 0.0)
        positions.add("$pair · cantidad ${"%.5f".format(amount)} · entrada ${"%.4f".format(rate)} · ${"%.2f".format(pnl)}%")
    }
    return Dashboard(
        state = bot.optString("state", "desconocido"),
        dryRun = bot.optBoolean("dry_run", false),
        exchange = bot.optString("exchange", "—"),
        timeframe = bot.optString("timeframe", "5m"),
        strategy = bot.optString("strategy", "—"),
        stakeCurrency = balance.optString("stake", bot.optString("stake_currency", "USDT")),
        openTrades = count.optInt("current", open.length()),
        maxOpenTrades = count.optInt("max", bot.optInt("max_open_trades", 0)),
        profit = profit.optDouble("profit_all_coin", profit.optDouble("profit_closed_coin", 0.0)),
        profitPct = profit.optDouble("profit_all_percent", profit.optDouble("profit_closed_percent", 0.0)),
        wallet = balance.optDouble("total", balance.optDouble("value", 0.0)),
        positions = positions,
        version = bot.optString("version", "—")
    )
}

@Composable
private fun TraderScreen() {
    var serverUrl by remember { mutableStateOf("") }
    var accessToken by remember { mutableStateOf("") }
    var dashboard by remember { mutableStateOf<Dashboard?>(null) }
    var isLoading by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("Conectá tu servidor para consultar el bot.") }
    val scope = rememberCoroutineScope()

    fun runRequest(path: String? = null, post: Boolean = false) {
        if (isLoading) return
        isLoading = true
        message = "Conectando con el servidor…"
        scope.launch {
            try {
                if (path != null) apiRequest(serverUrl, accessToken, path, post)
                val response = apiRequest(serverUrl, accessToken, "/api/dashboard")
                dashboard = parseDashboard(response)
                message = "Datos actualizados correctamente."
            } catch (e: Exception) {
                message = e.message ?: "No se pudo conectar. Revisá el servidor y el token."
            } finally {
                isLoading = false
            }
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().background(Navy).verticalScroll(rememberScrollState()).padding(18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Column {
                Text("CRYPTO AI", color = Mint, fontSize = 12.sp, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)
                Text("TRADER", color = Color.White, fontSize = 27.sp, fontWeight = FontWeight.ExtraBold)
            }
            Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(20.dp)) {
                Text("ANDROID  ·  v0.2", modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp), color = SoftText, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            }
        }

        Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(18.dp)) {
            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("CONEXIÓN SEGURA", color = Mint, fontSize = 12.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
                OutlinedTextField(value = serverUrl, onValueChange = { serverUrl = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("URL HTTPS del servidor") }, placeholder = { Text("https://trader.tudominio.com") })
                OutlinedTextField(value = accessToken, onValueChange = { accessToken = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, visualTransformation = PasswordVisualTransformation(), label = { Text("Token de acceso") })
                Button(onClick = { runRequest() }, enabled = !isLoading, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = Mint, contentColor = Navy)) {
                    if (isLoading) CircularProgressIndicator(modifier = Modifier.width(18.dp).height(18.dp), strokeWidth = 2.dp, color = Navy)
                    else Text("CONECTAR / ACTUALIZAR", fontWeight = FontWeight.Bold)
                }
                Text(message, color = SoftText, fontSize = 12.sp)
            }
        }

        dashboard?.let { data ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("PANEL DEL BOT", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                Text(if (data.dryRun) "SIMULACIÓN" else "MODO NO VERIFICADO", color = if (data.dryRun) Mint else Color(0xFFFFB86B), fontSize = 10.sp, fontWeight = FontWeight.Bold)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                MetricCard("RESULTADO", "${"%.4f".format(data.profit)} ${data.stakeCurrency}", "${"%.2f".format(data.profitPct)}%", Modifier.weight(1f))
                MetricCard("SALDO", "${"%.2f".format(data.wallet)}", data.stakeCurrency, Modifier.weight(1f))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                MetricCard("OPERACIONES", "${data.openTrades}", "de ${data.maxOpenTrades} permitidas", Modifier.weight(1f))
                MetricCard("ESTADO", data.state.uppercase(), "${data.exchange} · ${data.timeframe}", Modifier.weight(1f))
            }
            Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(18.dp)) {
                Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("CONTROL DE SIMULACIÓN", color = Mint, fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp)
                    Text("El control móvil solo permite iniciar, pausar o detener Freqtrade cuando el servidor confirma Dry-run.", color = SoftText, fontSize = 12.sp)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        Button(onClick = { runRequest("/api/bot/start", true) }, enabled = !isLoading && data.dryRun, modifier = Modifier.weight(1f), colors = ButtonDefaults.buttonColors(containerColor = Mint, contentColor = Navy)) { Text("INICIAR", fontWeight = FontWeight.Bold) }
                        OutlinedButton(onClick = { runRequest("/api/bot/pause", true) }, enabled = !isLoading && data.dryRun, modifier = Modifier.weight(1f)) { Text("PAUSAR") }
                        OutlinedButton(onClick = { runRequest("/api/bot/stop", true) }, enabled = !isLoading && data.dryRun, modifier = Modifier.weight(1f)) { Text("DETENER") }
                    }
                }
            }
            Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(18.dp)) {
                Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("POSICIONES ABIERTAS", color = Mint, fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp)
                    if (data.positions.isEmpty()) Text("No hay operaciones abiertas.", color = SoftText, fontSize = 13.sp)
                    else data.positions.forEach { Text(it, color = Color.White, fontSize = 12.sp); Divider(color = Color(0xFF29374D)) }
                }
            }
            Text("Estrategia: ${data.strategy} · Freqtrade ${data.version}", color = SoftText, fontSize = 11.sp)
        }
        Spacer(Modifier.height(16.dp))
        Text("El modo real no está disponible en esta versión. La app exige HTTPS y el servidor mantiene Dry-run activado.", color = SoftText, fontSize = 11.sp)
    }
}

@Composable
private fun MetricCard(title: String, value: String, subtitle: String, modifier: Modifier = Modifier) {
    Card(modifier = modifier, colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(17.dp)) {
        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(title, color = SoftText, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
            Text(value, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 19.sp)
            Text(subtitle, color = Mint, fontSize = 10.sp)
        }
    }
}
