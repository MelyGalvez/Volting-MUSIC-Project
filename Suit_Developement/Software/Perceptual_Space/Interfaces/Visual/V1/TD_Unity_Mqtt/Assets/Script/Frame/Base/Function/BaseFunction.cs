using System.Collections;
using UnityEngine;


namespace ToolFrame.BaseFunction
{
    public class BaseFunction : MonoBehaviour
    {
        [Header("退出游戏")]
        public bool OpenExitKey;
        public KeyCode ExitKey;

        public void Update()
        {
            if (OpenExitKey)
            {
                if (Input.GetKeyDown(ExitKey))
                {
#if UNITY_EDITOR
                    UnityEditor.EditorApplication.isPlaying = false;
#else
                    Application.Quit();
#endif
                }
            }
        }
    }
}