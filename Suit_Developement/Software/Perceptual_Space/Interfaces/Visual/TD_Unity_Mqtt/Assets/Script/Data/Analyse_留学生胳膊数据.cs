using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Globalization;

public class Analyse_留学生胳膊数据 : AnalyseBase
{
    public string LastTime = "", NowTime = "";
    public float Roll, Pitch, Yaw, Ax, Ay, Az, D1, D2;

    public override void init()
    {
        LastTime = "";
        NowTime = "";

        Roll = 0;
        Ax = 0;
    }

    public override void PushInfoEnd()
    {
        LastTime = NowTime;
    }

    public override IEnumerator ReadLine_To_Json(string strLine, Action<string> BackJson)
    {
        // Ignore les lignes vides
        if (string.IsNullOrWhiteSpace(strLine))
        {
            yield break;
        }

        // Ignore l'en-tête CSV
        if (strLine.StartsWith("time"))
        {
            yield break;
        }

        Debug.Log("Lecture ligne CSV : " + strLine);

        string[] tableHead = strLine.Split(',');

        // Vérifie le nombre de colonnes
        if (tableHead.Length < 9)
        {
            Debug.LogError("Ligne CSV invalide : " + strLine);
            yield break;
        }

        NowTime = tableHead[0];

        if (LastTime != "")
        {
            float time = TimeDiff(LastTime, NowTime);

            // Empêche les temps négatifs
            if (time > 0)
            {
                yield return new WaitForSeconds(time);
            }
        }

        try
        {
            Roll = float.Parse(tableHead[1], CultureInfo.InvariantCulture);
            Pitch = float.Parse(tableHead[2], CultureInfo.InvariantCulture);
            Yaw = float.Parse(tableHead[3], CultureInfo.InvariantCulture);

            Ax = float.Parse(tableHead[4], CultureInfo.InvariantCulture);
            Ay = float.Parse(tableHead[5], CultureInfo.InvariantCulture);
            Az = float.Parse(tableHead[6], CultureInfo.InvariantCulture);

            D1 = float.Parse(tableHead[7], CultureInfo.InvariantCulture);
            D2 = float.Parse(tableHead[8], CultureInfo.InvariantCulture);
        }
        catch (FormatException e)
        {
            Debug.LogError("Erreur de format dans la ligne CSV : " + strLine);
            Debug.LogError(e.Message);
            yield break;
        }

        BackJson.Invoke(JsonUtility.ToJson(this));
    }

    public override float TimeDiff(string LastTime, string NewTime)
    {
        float Lt = float.Parse(LastTime, CultureInfo.InvariantCulture);
        float Nt = float.Parse(NewTime, CultureInfo.InvariantCulture);

        return Nt - Lt;
    }
}