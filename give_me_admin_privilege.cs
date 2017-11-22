using System;
using System.Runtime.InteropServices;


namespace Kuma
{
    public class Program
    {
        [DllImport("user32.dll", EntryPoint="ShowWindow")]
        public static extern bool ShowWindow(ulong hWnd, int nCmdShow);

	[DllImport("user32.dll", EntryPoint="PostMessage")]
        public static extern bool PostMessage(ulong hWnd, uint Msg);

	static void Main(string[] args)
	{
	    ulong hWnd = ulong.Parse(args[0]);
	    if (args[1] == "close") {
	        PostMessage(hWnd, 16); // WM_CLOSE = 16
	    } else {
	        ShowWindow(hWnd, 9); // SW_RESTORE = 9
	    }
	}
    }
}
