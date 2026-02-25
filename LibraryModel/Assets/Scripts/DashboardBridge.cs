using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Text;

public class DashboardBridge : MonoBehaviour
{
    [Header("Servers")]
    public string edgeUrl = "http://localhost:5001";
    public string dashboardUrl = "http://localhost:5000";
    public float frameInterval = 1.0f;

    RailSensorController[] sensors;
    float timer;
    int failCount;

    void Start()
    {
        InvokeRepeating("TryFindSensors", 0.5f, 2f);
    }

    void TryFindSensors()
    {
        sensors = FindObjectsByType<RailSensorController>(FindObjectsSortMode.None);
        if (sensors != null && sensors.Length > 0)
        {
            CancelInvoke("TryFindSensors");
            Debug.Log($"[Bridge] Found {sensors.Length} sensors → Edge:{edgeUrl} Dashboard:{dashboardUrl}");
        }
    }

    void Update()
    {
        if (sensors == null || sensors.Length == 0) return;

        timer += Time.deltaTime;
        if (timer >= frameInterval)
        {
            timer = 0;
            foreach (var s in sensors)
            {
                if (s != null && s.sensorRT != null)
                    StartCoroutine(SendFrame(s));
            }
            SendStatus();
        }
    }

    public void SendTelemetry(string json)
    {
        StartCoroutine(Post(edgeUrl + "/api/telemetry", json));
        StartCoroutine(Post(dashboardUrl + "/api/telemetry", json));
    }

    IEnumerator SendFrame(RailSensorController sensor)
    {
        RenderTexture rt = sensor.sensorRT;
        if (rt == null) yield break;

        var prev = RenderTexture.active;
        RenderTexture.active = rt;
        var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
        tex.Apply();
        RenderTexture.active = prev;

        byte[] jpg = tex.EncodeToJPG(75);
        Destroy(tex);

        string b64 = System.Convert.ToBase64String(jpg);
        string json = "{\"sensor\":\"" + sensor.transform.name +
                       "\",\"frame\":\"" + b64 + "\"}";

        StartCoroutine(Post(edgeUrl + "/api/camera", json));
        StartCoroutine(Post(dashboardUrl + "/api/camera", json));

        yield break;
    }

    void SendStatus()
    {
        if (sensors == null) return;
        var sb = new StringBuilder("{");
        for (int i = 0; i < sensors.Length; i++)
        {
            if (i > 0) sb.Append(",");
            sb.Append("\"").Append(sensors[i].transform.name).Append("\":\"")
              .Append(sensors[i].statusText).Append("\"");
        }
        sb.Append("}");
        string json = sb.ToString();
        StartCoroutine(Post(edgeUrl + "/api/status", json));
        StartCoroutine(Post(dashboardUrl + "/api/status", json));
    }

    IEnumerator Post(string url, string json)
    {
        var req = new UnityWebRequest(url, "POST");
        req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");
        req.timeout = 2;
        yield return req.SendWebRequest();

        if (req.result == UnityWebRequest.Result.ConnectionError && failCount < 2)
        {
            failCount++;
            if (failCount == 1)
                Debug.LogWarning($"[Bridge] Cannot reach {url}. Run: bash scripts/start_all.sh");
        }
        else if (req.result == UnityWebRequest.Result.Success)
        {
            failCount = 0;
        }
        req.Dispose();
    }
}
