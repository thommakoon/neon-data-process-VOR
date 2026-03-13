function [dataEyeR,dataEyeL,dataHeadR,dataHeadL] = splitTest(e,h,headThreshold)
sigPos = logical(h > 0);%Determine positive and negatve values
cros = sigPos - circshift(sigPos,1); %get sign changes
crosPos = find(cros);
[a,~] = size(crosPos);
n = 2;
dataEyeR = [];
dataEyeL = [];
dataHeadR = [];
dataHeadL = [];
while n <= a
    dataHeadInt = h(crosPos(n-1):crosPos(n));
    dataEyeInt = e(crosPos(n-1):crosPos(n));
    if cros(crosPos(n-1)) == 1
        left = true;
    else
        left = false;
    end
    [preCheck,~] = max(abs(dataHeadInt));
    if preCheck > headThreshold
        if left
            dataEyeL = vertcat(dataEyeL,dataEyeInt);
            dataEyeL = vertcat(dataEyeL,(-1*dataEyeInt));
            dataHeadL = vertcat(dataHeadL,dataHeadInt);
            dataHeadL = vertcat(dataHeadL,(-1*dataHeadInt));
        else
            dataEyeR = vertcat(dataEyeR,dataEyeInt);
            dataEyeR = vertcat(dataEyeR,(-1*dataEyeInt));
            dataHeadR = vertcat(dataHeadR,dataHeadInt);
            dataHeadR = vertcat(dataHeadR,(-1*dataHeadInt));
        end
    end
    n = n + 1;
end
end
