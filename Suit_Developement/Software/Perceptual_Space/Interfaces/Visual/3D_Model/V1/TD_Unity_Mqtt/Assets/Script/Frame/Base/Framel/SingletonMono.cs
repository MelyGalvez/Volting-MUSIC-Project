using System;
using System.Collections;
using UnityEngine;


namespace ToolFrame
{
    public abstract class SingletonMono<T> : MonoBehaviour where T : SingletonMono<T>
    {
        public static T instance;

        protected virtual void Awake()
        {
            if (instance == null)
            {
                instance = this as T;
            }
        }
    }
}

namespace ToolFrame.Tool
{
    public class FrameTool
    {
        /// <summary>
        /// 遍历子物体并修改material
        /// </summary>
        /// <param name="OBJ"></param>
        public static void Setmaterials(Transform OBJ,Material material)
        {
            MeshRenderer[] mr = OBJ.GetComponentsInChildren<MeshRenderer>(true);
            foreach (var item in mr)
            {
                Material[] mat = new Material[mr.Length];
                for (int i = 0; i < mat.Length; i++)
                {
                    mat[i] = material;
                }
                item.materials = mat;
            }
        }


        /// <summary>
        /// 将string转为DateTime
        /// </summary>
        /// <param name="Str"></param>
        /// <param name="layout"></param>
        /// <returns></returns>
        public static DateTime StrToDateTime(string Str,string layout= "HH:mm:ss.fff")
        {
            return DateTime.ParseExact(Str, layout, null);
        }

        /// <summary>
        /// 返回时间差(秒)
        /// </summary>
        /// <returns></returns>
        public static double TimeDiff(DateTime last,DateTime Now)
        {
            return (Now - last).TotalSeconds;
        }
    }
}