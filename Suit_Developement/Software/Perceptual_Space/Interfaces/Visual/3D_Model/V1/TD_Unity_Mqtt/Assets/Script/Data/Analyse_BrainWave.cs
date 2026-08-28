using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Analyse_BrainWave : AnalyseBase
{
    public string LastTime = "", NowTime = "";
    public float Alpha, LowBeta, HighBeta;

    public override void init()
    {
        LastTime = "";
        NowTime = "";

        Alpha = 0;
        LowBeta = 0;
        HighBeta = 0;
    }

    public override IEnumerator ReadLine_To_Json(string strLine, Action<string> BackJson)
    {
        string[] tableHead = tableHead = strLine.Split(',');
        NowTime = tableHead[0];
        if (LastTime != "")
        {
            float time = TimeDiff(LastTime, NowTime);
            //Debug.Log(time);
            yield return new WaitForSeconds(time);
        }

        Alpha = float.Parse(tableHead[3]);
        LowBeta = float.Parse(tableHead[4]);
        HighBeta = float.Parse(tableHead[5]);


        BackJson.Invoke(JsonUtility.ToJson(this));
    }

    public override void PushInfoEnd()
    {
        LastTime = NowTime;
    }

    public override float TimeDiff(string LastTime, string NewTime)
    {
        DateTime Lt = DateTime.ParseExact(LastTime, "HH:mm:ss.fff", null);
        DateTime Nt = DateTime.ParseExact(NewTime, "HH:mm:ss.fff", null);
        return (float)((Nt - Lt).TotalSeconds);
    }
}
