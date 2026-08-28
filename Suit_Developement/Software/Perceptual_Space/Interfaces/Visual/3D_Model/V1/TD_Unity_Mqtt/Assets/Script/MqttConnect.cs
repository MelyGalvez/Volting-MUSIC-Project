using System;
using ToolFrame.MqttConnect;
using UnityEngine;
using uPLibrary.Networking.M2Mqtt.Messages;

public class MqttConnect : BaseMqttConnect
{
    public string Mqtt_IP = "192.168.31.33";
    public int Mqtt_Port = 1883;


    public Coroutine IE;
    protected override void Awake()
    {
        base.Awake();

        if (IE != null) StopCoroutine(IE);
        IE = StartCoroutine(ConnectHelp("CSVPush", Mqtt_IP, Mqtt_Port, null, null));
    }

    public override void Client_MqttMsgPublishReceived(object sender, MqttMsgPublishEventArgs e)
    {

    }
}
