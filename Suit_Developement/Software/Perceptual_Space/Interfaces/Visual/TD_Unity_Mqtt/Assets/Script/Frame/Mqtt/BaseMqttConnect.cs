using System;
using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Text.RegularExpressions;
using ToolFrame;
using UnityEngine;
using uPLibrary.Networking.M2Mqtt;
using uPLibrary.Networking.M2Mqtt.Messages;

namespace ToolFrame.MqttConnect
{
    public abstract class BaseMqttConnect : SingletonMono<BaseMqttConnect>
    {
        public MqttClient client;

        public bool IsConnect { get 
            {
                if (client == null)
                {
                    return false;
                }
                else if (client.IsConnected)
                {
                    return true;
                }
                
                return false;
            } }

        public IEnumerator ConnectHelp(string name, string ip,int port, string[] SubscribedList,Action<bool> ConnectAc)
        {

            client = new MqttClient(IPAddress.Parse(ip), port, false, null);

            try
            {
                client.Connect(name);

                if (client.IsConnected)
                {
                    Debug.Log("Mqtt连接成功:" + ip);

                    if (SubscribedList!=null)
                    {
                        byte[] bytes = new byte[SubscribedList.Length];
                        for (int i = 0; i < bytes.Length; i++)
                        {
                            bytes[i] = MqttMsgBase.QOS_LEVEL_EXACTLY_ONCE;
                        }

                        client.Subscribe(SubscribedList, bytes);

                        client.MqttMsgPublishReceived += Client_MqttMsgPublishReceived;
                    }

                    ConnectAc?.Invoke(true);
                }
                else
                {
                    ConnectAc?.Invoke(false);
                }
            }
            catch (Exception ex)
            {
                ConnectAc?.Invoke(false);

            }

            Debug.Log("Mqtt连接失败:" + ip);
            yield break;
        }

        public abstract void Client_MqttMsgPublishReceived(object sender, MqttMsgPublishEventArgs e);
        public virtual void Push(string topic, string Json)
        {
            if (instance.client != null)
            {
                if (instance.client.IsConnected)
                {
                    instance.client.Publish(topic, System.Text.Encoding.UTF8.GetBytes(Regex.Unescape(Json)));
                }

            }
        }
    }
}