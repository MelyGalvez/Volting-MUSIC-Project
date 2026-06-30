using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

public class CSV_Push : MonoBehaviour
{
    public MqttConnect mqttClient;
    private bool IsMqttConnect { get { return mqttClient.IsConnect; } }
    public void Push(string type, string info)
    {
        mqttClient.Push(type, info);
    }

    [Space]
    [Min(1)] public float hz = 1;
    public string filePath;
    [Space]
    public bool Loop;
    public bool Run;
    public bool Pause;
    public bool Next;
    public bool Rest;
    [Space]
    public int RowIndex;
    public AnalyseBase info;
    Coroutine CSV_IE;
    void Start()
    {
        StartCoroutine(Help());
    }
    public IEnumerator Help()
    {
        while (true)
        {
            yield return new WaitUntil(() => Run);
            CSV_IE=StartCoroutine(CSVPush());

            yield return new WaitUntil(() => Rest);
            Rest = false;
            Run = false;
            if (CSV_IE != null)
            {
                StopCoroutine(CSV_IE);
            }
        }
    }


    public IEnumerator CSVPush()
    {
        while (Loop)
        {
            RowIndex = 0;

            using (FileStream fs = new FileStream(filePath, FileMode.Open, FileAccess.Read))
            {
                using (StreamReader sr = new StreamReader(fs, Encoding.UTF8))
                {
                    string strLine = sr.ReadLine();
                    RowIndex++;
                    info.init();

                    string Json = "";
                    while ((strLine = sr.ReadLine()) != null)
                    {
                        RowIndex++;

                        yield return info.ReadLine_To_Json(strLine, (json) => { Json = json; });

                        Push("TD", Json);

                        info.PushInfoEnd();

                        if (Pause)
                        {
                            yield return new WaitUntil(() => !Pause || Next);
                            Next = false;
                        }
                    }
                }
            }
        }
    }

    public void OnDestroy()
    {
    }
}
