using UnityEngine;
using System.Collections;
using System.Net;
using System.Text;
using uPLibrary.Networking.M2Mqtt;
using uPLibrary.Networking.M2Mqtt.Messages;

public class Mqtt : MonoBehaviour
{

    private MqttClient mqttClient;

    void Awake()
    {
        //链接服务器  
        mqttClient = new MqttClient(IPAddress.Parse("192.168.1.126"), 61613, false, null);
      
        //注册服务器返回信息接受函数  
        mqttClient.MqttMsgPublishReceived += client_MqttMsgPublishReceived;
        //客户端ID  一个字符串  
        mqttClient.Connect("zsc");
        //监听FPS字段的返回数据  
        mqttClient.Subscribe(new string[] { "fps" }, new byte[] { MqttMsgBase.QOS_LEVEL_AT_LEAST_ONCE });
    }
    void Start()
    {

    }

    // Update is called once per frame  
    void Update()
    {

        if (Input.GetMouseButtonDown(0))
        {
            //这个字符串是向服务器发送的数据信息  
            string strValue = "123";
            // 发送一个内容是123 字段是klabs的信息  
            mqttClient.Publish("klabs", Encoding.UTF8.GetBytes(strValue));
            Debug.Log("发送数据123");
        }
    }

    static void client_MqttMsgPublishReceived(object sender, MqttMsgPublishEventArgs e)
    {
        // handle message received  
        Debug.Log("返回数据");
        string msg = System.Text.Encoding.Default.GetString(e.Message);
        Debug.Log(msg);
    }
}
