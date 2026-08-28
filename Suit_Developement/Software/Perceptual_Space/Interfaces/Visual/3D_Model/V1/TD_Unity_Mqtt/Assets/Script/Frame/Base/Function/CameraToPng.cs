using System;
using System.Collections;
using ToolFrame.BaseFunction;
using UnityEngine;


namespace ToolFrame.Tool
{
    public class CameraToPng : MonoBehaviour
    {
        [SerializeField] Camera cam;
        [SerializeField] Vector2Int Size = new Vector2Int(5760, 1080);
        [SerializeField][Tooltip("工程文件Asset的相对路径,后缀名默认为Png,路径不需要后缀名")] string Path_InApp = "Res/Bg";

        [SerializeField] bool activate_1;
        [SerializeField] bool activate_2;

        [ReadOnly][SerializeField] RenderTexture Rd;
        [ReadOnly][SerializeField] RenderTexture OrRd;
        private Coroutine coroutine;

        private void OnDrawGizmos()
        {
            if (activate_1)
            {
                activate_1 = false;
                Stage1();
            }

            if (activate_2)
            {
                activate_2 = false;
                Stage2();
            }
        }


        private void RunRdToPng_IE()
        {
            if (coroutine!=null)
            {
               StopCoroutine(coroutine);
            }

            coroutine= StartCoroutine(Help());
        }
        private IEnumerator Help()
        {

            // 创建 RenderTexture 并设置到相机上
            Rd = new RenderTexture(Size.x, Size.y, 0);
            cam.targetTexture = Rd;

            // 等待几帧让相机渲染到RenderTexture
            // 其实应当使用 cam.Render() 但会报错,所以才出此下策
            yield return 2;

            // 激活这个rt, 并从中读取像素。
            OrRd = RenderTexture.active;
            RenderTexture.active = Rd;

            // 创建2d贴图
            Texture2D screenShot = new Texture2D(Size.x, Size.y, TextureFormat.RGB24, false);
            screenShot.ReadPixels(new Rect(0, 0, Size.x, Size.y), 0, 0);// 注：这个时候，它是从RenderTexture.active中读取像素  
            screenShot.Apply();

            // 重置相机参数
            cam.targetTexture = null;
            RenderTexture.active = OrRd;

            GameObject.DestroyImmediate(Rd);

            // 最后将这些纹理数据，成一个png图片文件  
            byte[] bytes = screenShot.EncodeToPNG();
            string fullname = Application.dataPath + "/" + Path_InApp + ".png";
            System.IO.File.WriteAllBytes(fullname, bytes);
        }

        private void Stage1()
        {
            // 创建 RenderTexture 并设置到相机上
            Rd = new RenderTexture(Size.x, Size.y, 0);
            cam.targetTexture = Rd;
        }

        private void Stage2()
        {
            // 激活这个rt, 并从中读取像素。
            OrRd = RenderTexture.active;
            RenderTexture.active = Rd;

            // 创建2d贴图
            Texture2D screenShot = new Texture2D(Size.x, Size.y, TextureFormat.RGB24, false);
            screenShot.ReadPixels(new Rect(0, 0, Size.x, Size.y), 0, 0);// 注：这个时候，它是从RenderTexture.active中读取像素  
            screenShot.Apply();

            // 重置相机参数
            cam.targetTexture = null;
            RenderTexture.active = OrRd;

            GameObject.DestroyImmediate(Rd);

            // 最后将这些纹理数据，成一个png图片文件  
            byte[] bytes = screenShot.EncodeToPNG();
            string fullname = Application.dataPath + "/" + Path_InApp + ".png";
            System.IO.File.WriteAllBytes(fullname, bytes);
        }
    }
}
