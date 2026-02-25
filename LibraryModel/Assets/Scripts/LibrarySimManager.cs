using UnityEngine;
using System.Collections.Generic;

public class LibrarySimManager : MonoBehaviour
{
    [Header("Spawn Settings")]
    public int maxStudents = 7;
    public float minSpawnInterval = 8f;
    public float maxSpawnInterval = 18f;

    [Header("Behavior")]
    public float minStudyTime = 30f;
    public float maxStudyTime = 90f;
    public float waterBreakChance = 0.35f;
    public float ghostChance = 0.20f;

    ProfessionalLibrary library;
    List<SimStudent> students = new List<SimStudent>();
    HashSet<string> reserved = new HashSet<string>();
    List<GameObject> ghostBags = new List<GameObject>();
    float spawnTimer;
    float nextSpawn;
    int counter;

    public Vector3 waterCoolerPos { get; private set; }

    static readonly Color[] Shirts = {
        new Color(0.22f,0.38f,0.55f), new Color(0.55f,0.18f,0.20f),
        new Color(0.20f,0.45f,0.28f), new Color(0.85f,0.82f,0.75f),
        new Color(0.35f,0.35f,0.38f), new Color(0.15f,0.20f,0.38f),
        new Color(0.50f,0.32f,0.18f), new Color(0.20f,0.42f,0.50f),
        new Color(0.42f,0.35f,0.22f), new Color(0.60f,0.45f,0.55f),
    };
    static readonly Color[] Skins = {
        new Color(0.95f,0.87f,0.78f), new Color(0.82f,0.68f,0.55f),
        new Color(0.72f,0.55f,0.40f), new Color(0.58f,0.42f,0.30f),
        new Color(0.42f,0.30f,0.22f), new Color(0.78f,0.62f,0.48f),
    };
    static readonly Color[] Hairs = {
        new Color(0.08f,0.06f,0.05f), new Color(0.15f,0.10f,0.08f),
        new Color(0.32f,0.22f,0.14f), new Color(0.42f,0.18f,0.10f),
        new Color(0.38f,0.32f,0.22f),
    };
    static readonly Color[] Bags = {
        new Color(0.15f,0.15f,0.18f), new Color(0.15f,0.20f,0.35f),
        new Color(0.35f,0.35f,0.38f), new Color(0.48f,0.18f,0.15f),
        new Color(0.28f,0.32f,0.20f), new Color(0.35f,0.25f,0.15f),
    };
    static readonly Color[] Pants = {
        new Color(0.25f,0.25f,0.28f), new Color(0.15f,0.18f,0.28f),
        new Color(0.55f,0.48f,0.35f), new Color(0.12f,0.12f,0.14f),
    };
    static readonly Color[] Shoes = {
        new Color(0.18f,0.15f,0.12f), new Color(0.12f,0.12f,0.14f),
        new Color(0.35f,0.28f,0.20f), new Color(0.22f,0.22f,0.25f),
    };

    void Start()
    {
        library = FindFirstObjectByType<ProfessionalLibrary>();
        if (library == null) { Debug.LogError("[SimManager] No library found!"); enabled = false; return; }

        float hW = library.roomWidth / 2f;
        float hL = library.roomLength / 2f;
        waterCoolerPos = new Vector3(hW - 1.5f, 0, hL - 1.5f);

        nextSpawn = 2f;
        spawnTimer = 0;

        Debug.Log($"[SimManager] Ready. {library.GetTotalSeats()} seats available.");
    }

    void Update()
    {
        spawnTimer += Time.deltaTime;

        if (spawnTimer >= nextSpawn && students.Count < maxStudents)
        {
            SpawnStudent();
            spawnTimer = 0;
            nextSpawn = Random.Range(minSpawnInterval, maxSpawnInterval);
        }

        for (int i = students.Count - 1; i >= 0; i--)
        {
            if (students[i] == null || students[i].state == SimStudent.S.DONE)
            {
                var st = students[i];
                if (st != null)
                {
                    if (st.willGhostLeave)
                    {
                        var bag = GameObject.Find($"Student_{st.assignedSeatId}/Body/Bag");
                        Debug.Log($"[SimManager] Ghost occupancy at {st.assignedSeatId}");
                    }
                    reserved.Remove(st.assignedSeatId);
                    Destroy(st.gameObject);
                }
                students.RemoveAt(i);
            }
        }
    }

    void SpawnStudent()
    {
        string seatId = GetRandomSeat();
        if (seatId == null) return;

        counter++;
        float hL = library.roomLength / 2f;

        GameObject go = new GameObject($"Student_{counter}");
        go.transform.position = new Vector3(Random.Range(-0.5f, 0.5f), 0, hL - 0.5f);

        var sim = go.AddComponent<SimStudent>();
        sim.assignedSeatId = seatId;
        sim.walkSpeed = Random.Range(1.5f, 2.2f);
        sim.studyDuration = Random.Range(minStudyTime, maxStudyTime);
        sim.secondStudyDuration = Random.Range(15f, 40f);
        sim.willTakeWaterBreak = Random.value < waterBreakChance;
        sim.willGhostLeave = Random.value < ghostChance;

        sim.shirtColor = Pick(Shirts);
        sim.skinColor = Pick(Skins);
        sim.hairColor = Pick(Hairs);
        sim.bagColor = Pick(Bags);
        sim.pantsColor = Pick(Pants);
        sim.shoeColor = Pick(Shoes);
        sim.hasGlasses = Random.value < 0.25f;
        sim.bodyScale = Random.Range(0.95f, 1.05f);

        sim.Init(this, library);

        reserved.Add(seatId);
        students.Add(sim);

        string behavior = sim.willTakeWaterBreak ? "will take water break" : "straight study";
        if (sim.willGhostLeave) behavior += " + GHOST";
        Debug.Log($"[SimManager] Spawned student #{counter} → {seatId} ({behavior})");
    }

    string GetRandomSeat()
    {
        var available = new List<string>();
        foreach (var s in library.allSeats)
        {
            if (!reserved.Contains(s.seatId))
                available.Add(s.seatId);
        }
        if (available.Count == 0) return null;
        return available[Random.Range(0, available.Count)];
    }

    Color Pick(Color[] palette) => palette[Random.Range(0, palette.Length)];

    void OnDestroy()
    {
        foreach (var s in students)
            if (s != null) Destroy(s.gameObject);
        students.Clear();
        reserved.Clear();
    }
}
