using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public abstract class AnalyseBase : MonoBehaviour
{
    public abstract void init();

    public abstract IEnumerator ReadLine_To_Json(string strLine, Action<string> BackJson);

    public abstract void PushInfoEnd();


    public abstract float TimeDiff(string LastTime, string NewTime);
}
