using UnityEngine;
using System.Collections.Generic;

public class SimStudent : MonoBehaviour
{
    [HideInInspector] public string assignedSeatId;
    [HideInInspector] public float walkSpeed = 1.8f;
    [HideInInspector] public float studyDuration = 45f;
    [HideInInspector] public float secondStudyDuration = 25f;
    [HideInInspector] public bool willTakeWaterBreak;
    [HideInInspector] public bool willGhostLeave;
    [HideInInspector] public Color shirtColor, pantsColor, skinColor, hairColor;
    [HideInInspector] public Color bagColor, shoeColor;
    [HideInInspector] public bool hasGlasses;
    [HideInInspector] public float bodyScale = 1f;

    public enum S {
        SPAWN, WALK_TO_SEAT, SIT, PLACE, STUDY,
        STAND, WALK_TO_COOLER, DRINK, WALK_BACK,
        SIT2, STUDY2, PACK, STAND2, WALK_OUT, DONE
    }
    public S state { get; private set; } = S.SPAWN;

    LibrarySimManager mgr;
    ProfessionalLibrary lib;
    List<Vector3> wp = new List<Vector3>();
    int wpi;
    Vector3 chairP, deskP, standP, seatP;
    float cSide, timer, wCycle;
    GameObject body, bagO, lapO, bookO;
    Transform lL, lR;
    Transform kL, kR;
    bool placed;

    public void Init(LibrarySimManager m, ProfessionalLibrary l)
    {
        mgr = m; lib = l;
        if (!FindSeat()) { state = S.DONE; return; }
        BuildModel();
        PathToSeat();
        state = S.SPAWN; timer = 0;
    }

    bool FindSeat()
    {
        var s = lib.GetSeatById(assignedSeatId);
        if (s == null) return false;
        var ch = s.seatTransform.Find("Chair");
        var dk = s.seatTransform.Find("DeskTop");
        if (ch == null || dk == null) return false;
        chairP = ch.position;
        deskP = dk.position + Vector3.up * 0.04f;
        cSide = (ch.position.z > dk.position.z) ? 1f : -1f;
        return true;
    }

    void PathToSeat()
    {
        wp.Clear(); wpi = 0;
        float hL = lib.roomLength / 2f;
        wp.Add(new Vector3(0, 0, hL - 1.5f));
        wp.Add(new Vector3(0, 0, chairP.z));
        wp.Add(new Vector3(chairP.x, 0, chairP.z));
    }
    void PathToCooler()
    {
        wp.Clear(); wpi = 0;
        var c = mgr.waterCoolerPos;
        wp.Add(new Vector3(0, 0, chairP.z));
        wp.Add(new Vector3(0, 0, c.z));
        wp.Add(c + new Vector3(Random.Range(-0.3f, 0.3f), 0, 0.4f));
    }
    void PathBack()
    {
        wp.Clear(); wpi = 0;
        var c = mgr.waterCoolerPos;
        wp.Add(new Vector3(0, 0, c.z));
        wp.Add(new Vector3(0, 0, chairP.z));
        wp.Add(new Vector3(chairP.x, 0, chairP.z));
    }
    void PathOut()
    {
        wp.Clear(); wpi = 0;
        float hL = lib.roomLength / 2f;
        wp.Add(new Vector3(0, 0, chairP.z));
        wp.Add(new Vector3(0, 0, hL - 1f));
        wp.Add(new Vector3(0, 0, hL + 2f));
    }

    void Update()
    {
        timer += Time.deltaTime;
        switch (state)
        {
            case S.SPAWN: if (timer > 0.3f) { state = S.WALK_TO_SEAT; timer = 0; } break;
            case S.WALK_TO_SEAT: case S.WALK_TO_COOLER: case S.WALK_BACK: case S.WALK_OUT:
                Walk(); break;
            case S.SIT: case S.SIT2: Sit(); break;
            case S.PLACE: Place(); break;
            case S.STUDY: if (timer >= studyDuration) { timer = 0; state = willTakeWaterBreak ? S.STAND : S.PACK; } break;
            case S.STAND: case S.STAND2: Stand(); break;
            case S.DRINK: if (timer >= 4f) { timer = 0; PathBack(); state = S.WALK_BACK; } break;
            case S.STUDY2: if (timer >= secondStudyDuration) { timer = 0; state = S.PACK; } break;
            case S.PACK: Pack(); break;
        }
    }

    void Walk()
    {
        if (wpi >= wp.Count) { WalkDone(); return; }
        Vector3 t = wp[wpi]; t.y = 0;
        Vector3 me = transform.position; me.y = 0;
        Vector3 d = t - me;
        if (d.magnitude > 0.15f)
        {
            Vector3 dir = d.normalized;
            transform.position += dir * walkSpeed * Time.deltaTime;
            transform.position = new Vector3(transform.position.x, 0, transform.position.z);
            if (dir.sqrMagnitude > 0.001f)
                transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(dir), Time.deltaTime * 8f);
            Legs(true);
        }
        else { transform.position = new Vector3(t.x, 0, t.z); wpi++; }
    }

    void WalkDone()
    {
        Legs(false); timer = 0;
        switch (state)
        {
            case S.WALK_TO_SEAT: PrepSit(); state = S.SIT; break;
            case S.WALK_TO_COOLER:
                var dir = (mgr.waterCoolerPos - transform.position);
                dir.y = 0;
                if (dir.sqrMagnitude > 0.01f) transform.rotation = Quaternion.LookRotation(dir.normalized);
                state = S.DRINK; break;
            case S.WALK_BACK: PrepSit(); state = S.SIT2; break;
            case S.WALK_OUT: state = S.DONE; break;
        }
    }

    void PrepSit()
    {
        transform.rotation = Quaternion.LookRotation(new Vector3(0, 0, -cSide));
        standP = new Vector3(chairP.x, 0, chairP.z);
        float seatY = Mathf.Max(chairP.y + 0.45f - 0.83f, -0.35f);
        seatP = new Vector3(chairP.x, seatY, chairP.z - cSide * 0.08f);
    }

    void Sit()
    {
        float t = Mathf.SmoothStep(0, 1, Mathf.Clamp01(timer / 1f));
        transform.position = Vector3.Lerp(standP, seatP, t);
        if (lL && lR)
        {
            lL.localRotation = Quaternion.Euler(-t * 90, 0, 0);
            lR.localRotation = Quaternion.Euler(-t * 90, 0, 0);
        }
        if (kL && kR)
        {
            kL.localRotation = Quaternion.Euler(t * 90, 0, 0);
            kR.localRotation = Quaternion.Euler(t * 90, 0, 0);
        }
        if (t >= 1f)
        {
            timer = 0;
            if (state == S.SIT && !placed) state = S.PLACE;
            else if (state == S.SIT) state = S.STUDY;
            else state = S.STUDY2;
        }
    }

    void Stand()
    {
        float t = Mathf.SmoothStep(0, 1, Mathf.Clamp01(timer / 0.7f));
        transform.position = Vector3.Lerp(seatP, standP, t);
        if (lL && lR)
        {
            lL.localRotation = Quaternion.Euler(-(1 - t) * 90, 0, 0);
            lR.localRotation = Quaternion.Euler(-(1 - t) * 90, 0, 0);
        }
        if (kL && kR)
        {
            kL.localRotation = Quaternion.Euler((1 - t) * 90, 0, 0);
            kR.localRotation = Quaternion.Euler((1 - t) * 90, 0, 0);
        }
        if (t >= 1f)
        {
            Legs(false); timer = 0;
            if (state == S.STAND) { PathToCooler(); state = S.WALK_TO_COOLER; }
            else { PathOut(); state = S.WALK_OUT; }
        }
    }

    void Place()
    {
        float y = transform.eulerAngles.y;
        if (timer > 0.3f && bagO.transform.parent == body.transform)
        {
            bagO.transform.SetParent(null);
            bagO.transform.position = new Vector3(chairP.x + transform.right.x * 0.45f, 0.15f, chairP.z + transform.right.z * 0.45f);
            bagO.transform.rotation = Quaternion.Euler(0, y + 180f + 15f, 5f);
        }
        if (timer > 0.8f && lapO.transform.parent == body.transform)
        {
            lapO.transform.SetParent(null);
            lapO.transform.position = deskP + transform.forward * 0.05f;
            lapO.transform.rotation = Quaternion.Euler(0, y + 180f, 0);
        }
        if (timer > 1.3f && bookO.transform.parent == body.transform)
        {
            bookO.transform.SetParent(null);
            bookO.transform.position = deskP + transform.forward * 0.05f + transform.right * 0.24f;
            bookO.transform.rotation = Quaternion.Euler(0, y + 180f - 8f, 0);
            placed = true; state = S.STUDY; timer = 0;
        }
    }

    void Pack()
    {
        if (willGhostLeave)
        {
            if (timer > 0.3f && lapO != null && lapO.transform.parent != body.transform)
            {
                lapO.transform.SetParent(body.transform);
                lapO.transform.localPosition = V(0, 0.95f, -0.22f);
                lapO.transform.localRotation = Quaternion.identity;
            }
            if (timer > 0.5f && bagO != null && bagO.transform.parent != body.transform)
            {
                bagO.transform.position = new Vector3(chairP.x, 0.48f, chairP.z);
                bagO.transform.rotation = Quaternion.Euler(0, transform.eulerAngles.y + 180f, 0);
            }
            if (timer > 1.0f) { timer = 0; state = S.STAND2; }
        }
        else
        {
            if (timer > 0.3f && lapO != null && lapO.transform.parent != body.transform)
            {
                lapO.transform.SetParent(body.transform);
                lapO.transform.localPosition = V(0, 0.95f, -0.22f);
                lapO.transform.localRotation = Quaternion.identity;
            }
            if (timer > 0.6f && bookO != null && bookO.transform.parent != body.transform)
            {
                bookO.transform.SetParent(body.transform);
                bookO.transform.localPosition = V(0.25f, 0.90f, 0.08f);
                bookO.transform.localRotation = Quaternion.identity;
            }
            if (timer > 0.9f && bagO != null && bagO.transform.parent != body.transform)
            {
                bagO.transform.SetParent(body.transform);
                bagO.transform.localPosition = V(0, 0.95f, -0.18f);
                bagO.transform.localRotation = Quaternion.identity;
            }
            if (timer > 1.2f) { timer = 0; state = S.STAND2; }
        }
    }

    void Legs(bool walk)
    {
        if (!lL) return;
        if (walk)
        {
            wCycle += Time.deltaTime * 8;
            float s = Mathf.Sin(wCycle) * 25;
            lL.localRotation = Quaternion.Euler(s, 0, 0);
            lR.localRotation = Quaternion.Euler(-s, 0, 0);
            if (kL && kR)
            {
                float kBend = Mathf.Max(0, -Mathf.Sin(wCycle)) * 30;
                float kBend2 = Mathf.Max(0, Mathf.Sin(wCycle)) * 30;
                kL.localRotation = Quaternion.Euler(-kBend, 0, 0);
                kR.localRotation = Quaternion.Euler(-kBend2, 0, 0);
            }
        }
        else
        {
            lL.localRotation = Quaternion.identity;
            lR.localRotation = Quaternion.identity;
            if (kL) kL.localRotation = Quaternion.identity;
            if (kR) kR.localRotation = Quaternion.identity;
        }
    }

    void OnDestroy()
    {
        if (willGhostLeave) return;
        if (bagO && bagO.transform.parent != body?.transform) Destroy(bagO);
        if (lapO && lapO.transform.parent != body?.transform) Destroy(lapO);
        if (bookO && bookO.transform.parent != body?.transform) Destroy(bookO);
    }

    void BuildModel()
    {
        body = new GameObject("Body"); body.transform.SetParent(transform);
        body.transform.localPosition = Vector3.zero;
        body.transform.localScale = Vector3.one * bodyScale;

        P(body,"Torso",PrimitiveType.Cube,V(0,1.05f,0),V(0.34f,0.44f,0.18f),shirtColor);
        P(body,"Collar",PrimitiveType.Cube,V(0,1.28f,0.04f),V(0.16f,0.04f,0.06f),shirtColor*0.9f);
        P(body,"Head",PrimitiveType.Sphere,V(0,1.50f,0),V(0.22f,0.24f,0.22f),skinColor);
        P(body,"Hair",PrimitiveType.Sphere,V(0,1.56f,-0.02f),V(0.23f,0.16f,0.23f),hairColor);
        P(body,"HairF",PrimitiveType.Cube,V(0,1.58f,0.08f),V(0.18f,0.04f,0.04f),hairColor);
        P(body,"Neck",PrimitiveType.Cube,V(0,1.34f,0),V(0.08f,0.08f,0.08f),skinColor);
        P(body,"EyeL",PrimitiveType.Sphere,V(-0.04f,1.52f,0.10f),V(0.03f,0.03f,0.02f),C(0.15f,0.12f,0.10f));
        P(body,"EyeR",PrimitiveType.Sphere,V(0.04f,1.52f,0.10f),V(0.03f,0.03f,0.02f),C(0.15f,0.12f,0.10f));
        P(body,"Nose",PrimitiveType.Cube,V(0,1.48f,0.11f),V(0.02f,0.03f,0.02f),skinColor*0.95f);
        P(body,"EarL",PrimitiveType.Cube,V(-0.11f,1.50f,0),V(0.02f,0.04f,0.03f),skinColor*0.95f);
        P(body,"EarR",PrimitiveType.Cube,V(0.11f,1.50f,0),V(0.02f,0.04f,0.03f),skinColor*0.95f);
        if(hasGlasses){
            P(body,"GlL",PrimitiveType.Cube,V(-0.04f,1.52f,0.115f),V(0.035f,0.025f,0.005f),C(0.18f,0.18f,0.20f));
            P(body,"GlR",PrimitiveType.Cube,V(0.04f,1.52f,0.115f),V(0.035f,0.025f,0.005f),C(0.18f,0.18f,0.20f));
            P(body,"GlBr",PrimitiveType.Cube,V(0,1.52f,0.115f),V(0.03f,0.008f,0.005f),C(0.18f,0.18f,0.20f));
        }
        P(body,"ArmL",PrimitiveType.Cube,V(-0.22f,1.02f,0),V(0.10f,0.40f,0.10f),shirtColor);
        P(body,"HandL",PrimitiveType.Cube,V(-0.22f,0.78f,0),V(0.07f,0.08f,0.06f),skinColor);
        P(body,"ArmR",PrimitiveType.Cube,V(0.22f,1.02f,0),V(0.10f,0.40f,0.10f),shirtColor);
        P(body,"HandR",PrimitiveType.Cube,V(0.22f,0.78f,0),V(0.07f,0.08f,0.06f),skinColor);
        P(body,"Watch",PrimitiveType.Cube,V(-0.22f,0.82f,0.04f),V(0.04f,0.02f,0.05f),C(0.20f,0.20f,0.22f));

        var ll=new GameObject("HipL");ll.transform.SetParent(body.transform);ll.transform.localPosition=V(-0.08f,0.82f,0);
        P(ll,"Thigh",PrimitiveType.Cube,V(0,-0.12f,0),V(0.13f,0.24f,0.13f),pantsColor);
        var knL=new GameObject("KneeL");knL.transform.SetParent(ll.transform);knL.transform.localPosition=V(0,-0.24f,0);
        P(knL,"Shin",PrimitiveType.Cube,V(0,-0.10f,0),V(0.11f,0.20f,0.11f),pantsColor);
        P(knL,"Shoe",PrimitiveType.Cube,V(0,-0.22f,0.02f),V(0.10f,0.06f,0.15f),shoeColor);
        lL=ll.transform; kL=knL.transform;

        var rr=new GameObject("HipR");rr.transform.SetParent(body.transform);rr.transform.localPosition=V(0.08f,0.82f,0);
        P(rr,"Thigh",PrimitiveType.Cube,V(0,-0.12f,0),V(0.13f,0.24f,0.13f),pantsColor);
        var knR=new GameObject("KneeR");knR.transform.SetParent(rr.transform);knR.transform.localPosition=V(0,-0.24f,0);
        P(knR,"Shin",PrimitiveType.Cube,V(0,-0.10f,0),V(0.11f,0.20f,0.11f),pantsColor);
        P(knR,"Shoe",PrimitiveType.Cube,V(0,-0.22f,0.02f),V(0.10f,0.06f,0.15f),shoeColor);
        lR=rr.transform; kR=knR.transform;

        P(body,"Belt",PrimitiveType.Cube,V(0,0.83f,0),V(0.35f,0.04f,0.19f),C(0.22f,0.18f,0.12f));
        P(body,"Buckle",PrimitiveType.Cube,V(0,0.83f,0.10f),V(0.04f,0.03f,0.01f),C(0.65f,0.60f,0.40f));

        bagO=new GameObject("Bag");bagO.transform.SetParent(body.transform);bagO.transform.localPosition=V(0,0.95f,-0.18f);
        P(bagO,"Bd",PrimitiveType.Cube,Vector3.zero,V(0.28f,0.35f,0.14f),bagColor);
        P(bagO,"Fl",PrimitiveType.Cube,V(0,0.13f,0.05f),V(0.26f,0.10f,0.04f),bagColor*0.9f);
        P(bagO,"Zp",PrimitiveType.Cube,V(0,0.02f,0.075f),V(0.18f,0.008f,0.005f),C(0.65f,0.60f,0.40f));
        P(bagO,"SL",PrimitiveType.Cube,V(-0.10f,0.08f,0.06f),V(0.025f,0.30f,0.02f),bagColor*0.85f);
        P(bagO,"SR",PrimitiveType.Cube,V(0.10f,0.08f,0.06f),V(0.025f,0.30f,0.02f),bagColor*0.85f);

        lapO=new GameObject("Lap");lapO.transform.SetParent(body.transform);lapO.transform.localPosition=V(0,0.95f,-0.22f);
        P(lapO,"Bs",PrimitiveType.Cube,Vector3.zero,V(0.30f,0.015f,0.20f),C(0.55f,0.55f,0.58f));
        P(lapO,"KB",PrimitiveType.Cube,V(0,0.01f,-0.02f),V(0.24f,0.005f,0.12f),C(0.20f,0.20f,0.22f));
        var sc=P(lapO,"Sc",PrimitiveType.Cube,V(0,0.10f,-0.095f),V(0.30f,0.19f,0.01f),C(0.55f,0.55f,0.58f));
        sc.transform.localRotation=Quaternion.Euler(-15,0,0);
        P(sc,"Dp",PrimitiveType.Cube,V(0,0.005f,-0.006f),V(0.26f,0.15f,0.003f),C(0.18f,0.30f,0.50f));

        bookO=new GameObject("Bks");bookO.transform.SetParent(body.transform);bookO.transform.localPosition=V(0.25f,0.90f,0.08f);
        Color[]bc={C(0.55f,0.18f,0.15f),C(0.15f,0.28f,0.48f),C(0.18f,0.42f,0.22f)};
        for(int i=0;i<3;i++) P(bookO,$"B{i}",PrimitiveType.Cube,V(0,i*0.028f,0),V(0.16f,0.025f,0.22f),bc[i]);
        P(bookO,"Nb",PrimitiveType.Cube,V(0.01f,0.09f,0),V(0.14f,0.01f,0.20f),C(0.85f,0.82f,0.35f));
    }

    Vector3 V(float x,float y,float z)=>new Vector3(x,y,z);
    Color C(float r,float g,float b)=>new Color(r,g,b);
    GameObject P(GameObject p,string n,PrimitiveType t,Vector3 pos,Vector3 s,Color c){
        var o=GameObject.CreatePrimitive(t);o.name=n;o.transform.SetParent(p.transform);
        o.transform.localPosition=pos;o.transform.localScale=s;
        var rn=o.GetComponent<Renderer>();var m=new Material(rn.sharedMaterial);m.color=c;rn.sharedMaterial=m;
        DestroyImmediate(o.GetComponent<Collider>());return o;
    }
}
