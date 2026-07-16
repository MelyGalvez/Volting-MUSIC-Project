using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Xml;
using UnityEngine;

namespace ToolFrame.RunLog
{
    public class RunLog:SingletonMono<RunLog>
    {
        protected override void Awake()
        {
            base.Awake();

            Create();
        }

        //写入
        public static void Log(string log)
        {
            instance.Sw.WriteLine($"[{DateTime.Now.ToString(instance.TimeFormat)}] [Log] {log}");

            if (instance.NowWriteNum >= instance.AutoSave)
            {
                instance.fs.Flush();
                instance.Sw.Flush();

                instance.NowWriteNum = 0;
            }
            else
            {
                instance.NowWriteNum++;
            }
        }


        // 创建
        private string LogTxtPathDir = $@"{Application.streamingAssetsPath}/RunLog/";
        private string LogTxtPath = $@"{Application.streamingAssetsPath}/RunLog/Log.txt";
        private FileStream fs;
        private StreamWriter Sw;
        private RunLog Create()
        {
            //判断文件夹是否存在, 不存在则创建路径文件夹
            if (!Directory.Exists(LogTxtPathDir))
            {
                Directory.CreateDirectory(LogTxtPathDir);
            }

            //开启流写入
            fs = new FileStream(LogTxtPath, FileMode.Create, FileAccess.ReadWrite);
            Sw = new StreamWriter(fs);

            CreateConfig();
            ReadCconfig();
            RunLogInit();

            return instance;
        }

        // 配置
        private int NowWriteNum;
        private int AutoSave;
        private string TimeFormat;
        private bool OpenLogMessageReceived;
        private void CreateConfig()
        {
            string path = $@"{LogTxtPathDir}/Runlog.xml";
            if (!File.Exists(path))
            {
                FileStream fileStream = new FileStream(path, FileMode.OpenOrCreate);
                StreamWriter streamWriter = new StreamWriter(fileStream, System.Text.Encoding.UTF8);

                streamWriter.Write(
                    @"<?xml version=""1.0"" encoding=""UTF-8""?>
<config>
    <!-- 日志写入多少条后自动保存一次,放置崩溃时无日志(值太小频繁写入硬盘会有性能问题) -->
    <AutoSave_Num>50</AutoSave_Num>
    <!-- 日志时间格式 -->
    <TimeFormat>yyyy-MM-dd HH:mm:ss.fff</TimeFormat>
    <!-- 是否写入<unity.Debug.log>的输入,true/false -->
    <UnityLogMessageReceived >true</UnityLogMessageReceived>
</config>

"

                    );
                streamWriter.Close();
                fileStream.Close();
            }
        }

        private void ReadCconfig()
        {
            XmlDocument xmlDoc = new XmlDocument();
            xmlDoc.Load($@"{LogTxtPathDir}/Runlog.xml");

            // 读取-自动保存
            AutoSave = int.Parse(xmlDoc.SelectSingleNode("config/AutoSave_Num").InnerText);
            // 读取-时间格式
            TimeFormat = xmlDoc.SelectSingleNode("config/TimeFormat").InnerText;
            // 读取-写入Debug.log
            OpenLogMessageReceived = xmlDoc.SelectSingleNode("config/UnityLogMessageReceived").InnerText == "true" ? true : false;
        }

        private void RunLogInit()
        {
            if (OpenLogMessageReceived)
            {
                Application.logMessageReceived += RunlogDebugLogWrite;
            }
            Application.quitting += RunLogQuit;
        }

        private void RunLogQuit()
        {
            Log("正常退出游戏");
            Application.logMessageReceived-= RunlogDebugLogWrite;

            fs.Flush();
            Sw.Flush();

            Sw.Close();
            fs.Close();

            Sw.Dispose();
            fs.Dispose();
        }

        private void RunlogDebugLogWrite(string logString, string stackTrace, LogType type)
        {
            string time = DateTime.Now.ToString(instance.TimeFormat);

            // 根据日志类型，格式化输出
            switch (type)
            {
                case LogType.Error:
                case LogType.Exception:
                    instance.Sw.WriteLine($"[{time}] [ERROR] {logString}");
                    instance.Sw.WriteLine($"         StackTrace: {stackTrace}");
                    break;
                case LogType.Warning:
                    instance.Sw.WriteLine($"[{time}] [WARNING] {logString}");
                    break;
                default:
                    instance.Sw.WriteLine($"[{time}] [INFO] {logString}");
                    break;
            }

            if (NowWriteNum >= AutoSave)
            {
                fs.Flush();
                Sw.Flush();

                NowWriteNum = 0;
            }
            else
            {
                NowWriteNum++;
            }
        }
    }
}
