using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

namespace ToolFrame.ApiConnect
{
    public abstract class ApiConnect
    {
        public string Apiurl;
        public string Method;



        protected ApiConnect(string apiurl, string method)
        {
            Apiurl = apiurl;
            Method = method;
        }



        public bool IsRunPush { get; protected set; }

        protected virtual IEnumerator PushApiurl(string jsonBody)
        {
            // 更新状态
            IsRunPush = true;

            // 发送消息
            UnityWebRequest request = CreateWebRequest(Apiurl, Method, jsonBody);
            yield return request.SendWebRequest();

            // 检查返回消息
            if (IsRequestError(request.result))
            {
                Debug.LogError($"API Error: {request.responseCode}\n{request.downloadHandler.text}");
                IsRunPush = false;
                RequestErrot(request);
                yield break;
            }

            RequestReturn(request);
        }

        protected virtual void RequestErrot(UnityWebRequest request)
        {

        }

        protected virtual void RequestReturn(UnityWebRequest request)
        {

        }

        /// <summary>
        /// 创建UnityWebRequest对象,用于发送消息
        /// </summary>
        /// <param name="apiUrl"></param>
        /// <param name="Method"></param>
        /// <param name="jsonBody"></param>
        /// <returns></returns>
        protected virtual UnityWebRequest CreateWebRequest(string apiUrl, string Method, string jsonBody)
        {
            byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(jsonBody);
            var request = new UnityWebRequest(apiUrl, Method);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);// 设置上传处理器
            request.downloadHandler = new DownloadHandlerBuffer();// 设置下载处理器

            request.SetRequestHeader("Content-Type", "application/json");// 设置请求头
            request.SetRequestHeader("Accept", "*/*");// 设置接受类型
            return request;
        }

        /// <summary>
        /// 检查返回状态状态
        /// </summary>
        /// <param name="state"></param>
        /// <returns></returns>
        private bool IsRequestError(UnityWebRequest.Result state)
        {
            return state == UnityWebRequest.Result.ConnectionError ||
                   state == UnityWebRequest.Result.ProtocolError ||
                   state == UnityWebRequest.Result.DataProcessingError;
        }
    }
}
