using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using UnityEditor;
using UnityEditor.PackageManager;
using UnityEngine;
using uPLibrary.Networking.M2Mqtt;
using uPLibrary.Networking.M2Mqtt.Messages;

public class Matrix_Push : MonoBehaviour
{
    public MqttConnect mqttClient;
    private bool IsMqttConnect { get { return mqttClient.IsConnect; } }

    public List<int[]> Array = new List<int[]>();
    [Space]
    public int StartArray;
    public int EndArray;
    public bool IsPush;
    [Space]
    public float Speed;
    public bool IErun;
    public Coroutine IeHelp;
    void Start()
    {
        Array.Clear();
        Array.Add(new int[16] { 14, 7, 2, 11, 4, 9, 16, 5, 15, 6, 3, 10, 1, 12, 13, 8 });
        Array.Add(new int[16] { 7, 12, 1, 14, 2, 13, 8, 11, 16, 3, 10, 5, 9, 6, 15, 4 });
        Array.Add(new int[16] { 8, 11, 14, 1, 13, 2, 7, 12, 3, 16, 9, 6, 10, 5, 4, 15 });
    }
    public void FixedUpdate()
    {
        if (IsMqttConnect && IsPush && !IErun)
        {
            IsPush = false;
            StartIEPush(Array[StartArray], Array[EndArray], Speed);
        }
    }

    public void StartIEPush(int[] Start, int[] end, float Speed)
    {
        if (IErun)
        {
            StopCoroutine(IeHelp);
        }

        IeHelp = StartCoroutine(Help(Start, end, Speed));
    }
    public void EndIEPush()
    {
        if (IErun)
        {
            StopCoroutine(IeHelp);
        }
    }

    private IEnumerator Help(int[] Start, int[] end, float Speed)
    {
        IErun = true;

        if (Start.Length != end.Length)
        {
            Debug.LogError("两个数组大小不一致");
            yield break;
        }

        float[] pushList = new float[Start.Length];
        for (int i = 0; i < pushList.Length; i++)
        {
            pushList[i] = Start[i];
            PushInfo(i.ToString(), pushList[i].ToString("F3"));
        }

        int IsWhile = 0;
        while (IsWhile < Start.Length)
        {
            IsWhile = 0;
            for (int i = 0; i < Start.Length; i++)
            {
                if (Start[i] > end[i])
                {
                    pushList[i] -= Speed * Time.fixedDeltaTime;
                    pushList[i] = Mathf.Clamp(pushList[i], end[i], Start[i]);
                    PushInfo(i.ToString(), pushList[i].ToString("F3"));

                    if (pushList[i] <= end[i])
                    {
                        IsWhile++;
                    }
                }
                else if (Start[i] < end[i])
                {
                    pushList[i] += Speed * Time.fixedDeltaTime;
                    pushList[i] = Mathf.Clamp(pushList[i], Start[i], end[i]);
                    PushInfo(i.ToString(), pushList[i].ToString("F3"));

                    if (pushList[i]>= end[i])
                    {
                        IsWhile++;
                    }
                }
                else
                {
                    IsWhile++;
                }
            }

            yield return new WaitForFixedUpdate();
        }

        IErun = false;
    }


    public void PushInfo(string type, string info)
    {
        mqttClient.Push(type, info);
    }
}
