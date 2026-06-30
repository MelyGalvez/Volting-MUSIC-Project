using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace ToolFrame.Csv
{
    public abstract class BaseCsvData
    {
        public bool IsRun { private set; get; }

        [SerializeField] string Path = "";

        FileStream fs;
        StreamWriter Sw;

        public BaseCsvData(string path)
        {
            this.Path = path;
        }

        /// <summary>
        /// 判断csv路径是否有相同的文件
        /// </summary>
        /// <param name="DirectoryName">文件夹路径</param>
        /// <param name="CsvName">csv文件名</param>
        /// <returns>false:没有同名文件</returns>
        public virtual bool GetIsSameName(string DirectoryName, string CsvName)
        {
            string path = string.Format("{0}/{1}", Path, DirectoryName);

            // 目录不存在自然就没有相同的文件名
            if (!Directory.Exists(path)) return false;

            // 获取目录信息
            DirectoryInfo directoryInfo = new DirectoryInfo(path);
            // 获取所有文件信息
            FileInfo[] files = directoryInfo.GetFiles("*", SearchOption.AllDirectories);

            List<string> names = new List<string>();
            foreach (FileInfo file in files)
            {
                if (file.Name == CsvName)
                {
                    return true;
                }
            }

            return false;
        }

        /// <summary>
        /// 创建Csv数据流
        /// </summary>
        /// <param name="DirectoryName">文件夹路径</param>
        /// <param name="CsvName">csv文件名</param>
        public virtual void CreateCsvStream(string DirectoryName, string CsvName)
        {
            //判断文件夹是否存在, 不存在则创建路径文件夹
            string path = string.Format("{0}/{1}", Path, DirectoryName);
            if (!Directory.Exists(path))
            {
                Debug.Log(path);
                Directory.CreateDirectory(path);
            }

            path = string.Format("{0}/{1}", path, CsvName);
            fs = new FileStream(path, FileMode.CreateNew, FileAccess.ReadWrite);
            Sw = new StreamWriter(fs);

            IsRun = true;
            Debug.Log(path);
        }

        /// <summary>
        /// 停止数据流并保存Csv文件
        /// </summary>
        public virtual void StopStream()
        {
            if (!IsRun) return;

            IsRun = false;

            Debug.Log("结束流: "+fs.Name);

            fs.Flush();
            Sw.Flush();

            Sw.Close();
            fs.Close();

            Sw.Dispose();
            fs.Dispose();
        }

        /// <summary>
        /// 将目前在内存的数据流写入文件保存，适当的调用可以减少内存，但调用时可能会占用性能导致卡顿
        /// </summary>
        public virtual void FlushStream()
        {
            if (!IsRun) return;
            fs.Flush();
            Sw.Flush();
        }

        /// <summary>
        /// 写入csv内容
        /// </summary>
        /// <param name="str">内容    Csv是用逗号隔开噢</param>
        public virtual void WriteLine(string str)
        {
            if (!IsRun) return;
            Sw.WriteLine(str);
        }
    }
}