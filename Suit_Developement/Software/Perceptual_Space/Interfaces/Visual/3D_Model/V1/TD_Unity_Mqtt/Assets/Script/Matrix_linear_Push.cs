using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Matrix_linear_Push : MonoBehaviour
{
    public MqttConnect mqttClient;
    private bool IsMqttConnect { get { return mqttClient.IsConnect; } }
    public void Push(string type, string info)
    {
        mqttClient.Push(type, info);
    }

    [Space]
    public List<int[]> Array = new List<int[]>();
    [Min(1)] public float hz = 1;
    public bool Run;
    [Space]
    public bool Rest;
    [Tooltip("选择数组")] public int Index;
    [Tooltip("当前目标")] public int Array_i;
    public float NowValue;
    void Start()
    {
        Array.Clear();
        Array.Add(new int[16] { 14, 7, 2, 11, 4, 9, 16, 5, 15, 6, 3, 10, 1, 12, 13, 8 });
        Array.Add(new int[16] { 7, 12, 1, 14, 2, 13, 8, 11, 16, 3, 10, 5, 9, 6, 15, 4 });
        Array.Add(new int[16] { 8, 11, 14, 1, 13, 2, 7, 12, 3, 16, 9, 6, 10, 5, 4, 15 });

        StartCoroutine(Help());
    }

    public IEnumerator Help()
    {
        yield return new WaitUntil(() => Run);
        while (true)
        {
            if (Rest) { Rest = false; Array_i = 0; NowValue = 0; }


            Push("0", Array[Index][Array_i].ToString());
            yield return new WaitForSeconds(1f/ hz);

            Array_i++;

            if (Array_i > Array[Index].Length - 1)
            {
                Array_i = 0;
                Run = false;
                yield return new WaitUntil(() => Run);
            }
        }
    }

    public void OnDestroy()
    {
        Push("0", 0.ToString());
    }
}
