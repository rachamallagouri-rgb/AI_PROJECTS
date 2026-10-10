package com.asianagni.ramai

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import org.json.JSONObject
import java.io.BufferedReader
import java.io.DataOutputStream
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

object ApiClient {
    data class Result(val ok: Boolean, val code: Int, val body: String)

    private fun open(path: String): HttpURLConnection {
        val base = BuildConfig.API_BASE_URL.trimEnd('/')
        return (URL(base + path).openConnection() as HttpURLConnection).apply {
            connectTimeout = 15_000
            readTimeout = 120_000
            setRequestProperty("Accept", "application/json")
        }
    }

    fun get(path: String, token: String? = null): Result {
        val conn = open(path)
        conn.requestMethod = "GET"
        token?.let { conn.setRequestProperty("Authorization", "Bearer $it") }
        return read(conn)
    }

    fun delete(path: String, token: String? = null): Result {
        val conn = open(path)
        conn.requestMethod = "DELETE"
        token?.let { conn.setRequestProperty("Authorization", "Bearer $it") }
        return read(conn)
    }

    fun postJson(path: String, json: JSONObject, token: String? = null): Result {
        val conn = open(path)
        conn.requestMethod = "POST"
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        token?.let { conn.setRequestProperty("Authorization", "Bearer $it") }
        conn.outputStream.bufferedWriter(Charsets.UTF_8).use { it.write(json.toString()) }
        return read(conn)
    }

    fun upload(
        path: String,
        uri: Uri,
        resolver: ContentResolver,
        token: String?
    ): Result {
        val boundary = "RAMAI-${UUID.randomUUID()}"
        val conn = open(path)
        conn.requestMethod = "POST"
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
        token?.let { conn.setRequestProperty("Authorization", "Bearer $it") }

        val name = queryName(resolver, uri) ?: "input.bin"
        val mime = resolver.getType(uri) ?: "application/octet-stream"
        DataOutputStream(conn.outputStream).use { out ->
            out.writeBytes("--$boundary\r\n")
            out.writeBytes("Content-Disposition: form-data; name=\"file\"; filename=\"$name\"\r\n")
            out.writeBytes("Content-Type: $mime\r\n\r\n")
            resolver.openInputStream(uri)?.use { input -> input.copyTo(out) }
                ?: error("Unable to open selected file")
            out.writeBytes("\r\n--$boundary--\r\n")
            out.flush()
        }
        return read(conn)
    }

    private fun queryName(resolver: ContentResolver, uri: Uri): String? {
        resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) return cursor.getString(0)
        }
        return uri.lastPathSegment
    }

    private fun read(conn: HttpURLConnection): Result {
        val code = conn.responseCode
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
        val body = if (stream != null) {
            BufferedReader(InputStreamReader(stream)).use { it.readText() }
        } else ""
        conn.disconnect()
        return Result(code in 200..299, code, body)
    }
}
