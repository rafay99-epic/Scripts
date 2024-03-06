#!/bin/bash

clear
echo -ne "
-------------------------------------------------------------------------
                   --- Reboot Script ---
-------------------------------------------------------------------------
"
echo -ne "
-------------------------------------------------------------------------
            --- Reboot is Required ---

Enter Your Choice:
        
        Press Yes for a complete Reboot
        Press No to Abort & Exit Application

        Enter Your Choice: 
-------------------------------------------------------------------------
"
read -p  ' ' user_choice

if [[ "$user_choice" == "yes" || "$user_choice" == "Yes" || "$user_choice" == "YES" || "$user_choice" == "yEs" || "$user_choice" == "yeS"  ]];
then 
    echo -ne "
                ---------------------------------------------------------------------------------------
                            Enter Password for Reboot                
                ---------------------------------------------------------------------------------------
            "
        sudo reboot now
elif [[ "$user_choice" == "no" || "$user_choice" == "No" || "$user_choice" == "nO" || "$user_choice" == "NO" ]];
then     
    # Display messgae Abbord 
    echo -ne "
                ---------------------------------------------------------------------------------------
                           --- Aborting & Exiting Application & System Complete ---    
                                    --- Good Bye!! Have a Nice Day ---           
                ---------------------------------------------------------------------------------------
            "
    cd restart
    chmod -x reboot.sh
    cd ../
    exit 0              
else
    #error occured message display  
    echo -ne "
                ---------------------------------------------------------------------------------------
                             --- Error Occured & Exiting Application ---                
                ---------------------------------------------------------------------------------------
            "
    exit 0
fi

