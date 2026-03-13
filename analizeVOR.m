% Jorge Rey Martinez 2021 version 2.0
% Inputs
% t = time array
% e = eye velocity array
% h = head velocity array
% s = Boolean, true if register is supresed VVOR false if VVOR
function analizeVOR(t,e,h,s)

%Draw figure considering screen size
scrsz = get(groot,'ScreenSize');

if s == 1
    figure1 = figure('Name','VORS ANALYSIS','NumberTitle','off','Position',[5 50 scrsz(3)/1.01 scrsz(4)/1.2]);
else
    figure1 = figure('Name','VVOR ANALYSIS','NumberTitle','off','Position',[5 50 scrsz(3)/1.01 scrsz(4)/1.2]);
end
figure(figure1);

%%%%%% Numerical data CALCULATIONS section %%%%%%%%%%%%

% Get Desacade eye data
if s == 1
    desacE = medfilt1(e,35);
else
    desacE = medfilt1(e,30);
end
%get positive/neagtive data
limit = size(t);
posH = [];
posE = [];
negH = [];
negE = [];
for n = 1:limit
    if h(n) > 0
        posH = vertcat(posH,h(n));
        if desacE(n) > 0
            posE = vertcat(posE,desacE(n));
        else
            posE = vertcat(posE,0);
        end
    end
    if h(n) < 0
        negH = vertcat(negH,h(n));
        if desacE(n) < 0
            negE = vertcat(negE,desacE(n));
        else
            negE = vertcat(negE,0);
        end
    end
end

prePosPeakE = mean(findpeaks(posE));
preNegPeakE = mean(findpeaks(abs(negE)));
if prePosPeakE > preNegPeakE
    peakE = prePosPeakE;
    peakH = mean(findpeaks(posH));
else
    peakE = -preNegPeakE;
    peakH = -mean(findpeaks(abs(negH)));
end

%AUC Gain
aucPosEye = trapz(posE);
aucPosHead = trapz(posH);
aucNegEye = trapz(negE);
aucNegHead = trapz(negH);
gainPos = (aucPosEye/aucPosHead);
gainNeg = (aucNegEye/aucNegHead);

%Eye Head Regression Gain
negB = negH\negE;
posB = posH\posE;
calcNegE = negB*negH;
calcPosE = posB*posH;

%Fourier based Gain calcullation algorithm
headThreshold = 20; % Set minimum head velocity for frequency analysis
[dataEyeR,dataEyeL,dataHeadR,dataHeadL] = splitTest(desacE,h,headThreshold);
[fHeadL,P1HeadL] = fourier(dataHeadL);
[fEyeL,P1EyeL] = fourier(dataEyeL);
[fHeadR,P1HeadR] = fourier(dataHeadR);
[fEyeR,P1EyeR] = fourier(dataEyeR);
[maxHeadPwrR,HeadPwrRIndex] = max(P1HeadR);
[maxHeadPwrL,HeadPwrLIndex] = max(P1HeadL);
maxHeadRFreq = fHeadR(HeadPwrRIndex);
maxHeadLFreq = fHeadL(HeadPwrLIndex);
[preMaxEyeRFreq,maxEyeRFreqIndex]=min(abs(fEyeR-maxHeadRFreq));
[preMaxEyeLFreq,maxEyeLFreqIndex]=min(abs(fEyeL-maxHeadLFreq));
maxEyeRFreq = fEyeR(maxEyeRFreqIndex);
maxEyeLFreq = fEyeL(maxEyeLFreqIndex);
maxEyeRPwr = P1EyeR(maxEyeRFreqIndex);
maxEyeLPwr = P1EyeL(maxEyeLFreqIndex);
leftFouGain = (maxEyeLPwr/maxHeadPwrL);
rightFouGain = (maxEyeRPwr/maxHeadPwrR);

%Analysis of head oscillations variability:
distanciaPicos = 60;
lHeadPeaks = findpeaks(posH,'MinPeakDistance',distanciaPicos);
rHeadPeaks = findpeaks(abs(negH),'MinPeakDistance',distanciaPicos);
velocityTreshold = 25;
lHeadInvalids = lHeadPeaks<velocityTreshold;
rHeadInvalids = rHeadPeaks<velocityTreshold;
lHeadPeaks(lHeadInvalids) = [];
rHeadPeaks(rHeadInvalids) = [];
[lPeakN, ~] = size(lHeadPeaks);
[rPeakN, ~] = size(rHeadPeaks);
[lPR,rPR,saccadePositions] = prScoreVVR(t,e,h,s);

%PR PLOT only available in VVOR tests
if s ~= 1
    subplot(3,2,5)
    plot(t,h,'b',t,e,'r','LineWidth',1.5)
    prTitle = strcat('Saccade Recognition & PR Plot || ', '  LEFT PR:',num2str(lPR),',  RIGHT PR: ',num2str(rPR));
    title(prTitle)
    xlabel('Time in samples')
    ylabel('Velocity in deg/sec')
    ylim([-400 +400])
    %add saccade detection to plot
    [sP,~,~] = find(t==saccadePositions);
    hold on
    plot(t(sP),e(sP),'ko')
    hold off
    legend ('Head velocity','Eye velocity','Detected Saccade')
end



%%%%% PLOTS SECTION %%%%%

%RAW plot
subplot(3,2,1)
plot(t,h,'b',t,e,'r','LineWidth',1.25)
title('Test Output - RAW data')
xlabel('Time in secs')
ylabel('Velocity in deg/sec')
ylim([-400 +400])
legend ('Head velocity','Eye velocity')

%Desaccaded plot
subplot(3,2,2)
plot(t,h,'b',t,desacE,'r','LineWidth',1.25)
AUCTitle = strcat('Test Output - Desaccaded data  || ',' LEFT GAIN: ',num2str(gainPos),' - RIGHT GAIN: ',num2str(gainNeg));
title(AUCTitle)
xlabel('Time in secs')
ylabel('Velocity in deg/sec')
ylim([-400 +400])
legend ('Head velocity','Eye velocity')


%XY ploy & regresion line
subplot(3,2,6)
hold on
if isOctave
    scatter(negH,negE,'c','.');
    scatter(posH,posE,'b','.');
else
    scatter(negH,negE,'.b');
    scatter(posH,posE,'.','MarkerEdgeColor',[0 .7 .7]);
end
XYTitle = strcat('Head vs Eye plot - Desaccaded data ||',' LEFT GAIN: ',num2str(posB),' - RIGHT GAIN: ',num2str(negB));
title(XYTitle)
xlabel('Head Velocity in deg/sec')
ylabel('Eye Velocity in deg/sec')
plot(negH,calcNegE,posH,calcPosE,'LineWidth',5)
if s == 1
    plot(negH,negH,'r',posH,posH,'r','LineWidth',1.5)
    legend ('Negative data','Positive data','Negative regresion','Positive regresion','No Suppression line','Location','northwest')
else
    plot(negH,negH,'g',posH,posH,'g','LineWidth',1.5)
    legend ('Negative data','Positive data','Negative regresion','Positive regresion','Normality line','Location','northwest')
end
hold off
%axis square
%Fourier plot of head and eye velocities
subplot(3,2,3)
[fHead,P1Head] = fourier(h);
[fEye,P1Eye] = fourier(e);

% -------------------------------
% Spectral Periodicity Index (SPI)
% Ratio of dominant peak to total spectral energy
% Values:
%   ~1.0 → highly periodic (ideal sine wave)
%   <0.5 → less periodic, irregular or noisy signal
% -------------------------------
SPI_head = max(P1Head) / sum(P1Head);
SPI_eye  = max(P1Eye)  / sum(P1Eye);

% -------------------------------
% Spectral Signal-to-Noise Ratio (SNR) in dB
% Compares dominant frequency power to remaining energy
% Values:
%   >10 dB → good periodic signal
%   ~0–5 dB → weak or noisy periodicity
% -------------------------------
SNR_head = 10 * log10(max(P1Head) / (sum(P1Head) - max(P1Head)));
SNR_eye  = 10 * log10(max(P1Eye)  / (sum(P1Eye)  - max(P1Eye)));

% Dominant frequency for head signal
[~,ixx] = max(P1Head);
maxFreqHeadFour = fHead(ixx);

% Plot head and eye spectrum
hold on
stem(fHead,P1Head,'b');  % Head spectrum
fourierTitle = sprintf('Head Spectrum || Freq(Hz): %.2f | SPI: %.2f | SNR: %.1f dB', ...
                       maxFreqHeadFour, SPI_head, SNR_head);
title(fourierTitle)
xlabel('f (Hz)')
ylabel('|P1(f)|')
xlim([0 5])
stem(fEye,P1Eye,'r');  % Eye spectrum
legend('Head','Eye')
hold off

% For FourierGain debug purposes only (uncoment next section)
% fgFigure = figure;
% subplot(2,2,3)
% hold on
% stem(fHeadL,P1HeadL,'b');
% title('Single-Side Amplitude Spectrum of Head and Eye (Desaccaded) || LEFT')
% xlabel('f (Hz)')
% ylabel('|P1(f)|')
% xlim([0 5])
% stem(fEyeL,P1EyeL,'r');
% legend('Head','Eye')
% hold off
% 
% subplot(2,2,4)
% hold on
% stem(fHeadR,P1HeadR,'b');
% title('Single-Side Amplitude Spectrum of Head and Eye (Desaccaded) || RIGHT')
% xlabel('f (Hz)')
% ylabel('|P1(f)|')
% xlim([0 5])
% stem(fEyeR,P1EyeR,'r');
% legend('Head','Eye')
% hold off
% 
% subplot(2,2,1)
% hold on
% plot(dataHeadL,'b','LineWidth',1.25)
% plot(dataEyeL,'r','LineWidth',1.25)
% hold off
% title('Test Output - LEFT SIDE')
% xlabel('Samples')
% ylabel('Velocity in deg/sec')
% ylim([-400 +400])
% legend ('Head velocity','Eye velocity')
% 
% subplot(2,2,2)
% hold on
% plot(dataHeadR,'b','LineWidth',1.25)
% plot(dataEyeR,'r','LineWidth',1.25)
% hold off
% title('Test Output - RIGHT SIDE')
% xlabel('Samples')
% ylabel('Velocity in deg/sec')
% ylim([-400 +400])
% legend ('Head velocity','Eye velocity')
% 
% set(0, 'currentfigure', figure1);


%%%%%%%%%Output analysis results to text%%%%%%%%%%%%

resultG = strcat('GAIN RESULTS: ',' Left(area): ',num2str(gainPos),' Right(area): ',num2str(gainNeg),' || Left(slope): ',num2str(posB),' Right(slope): ',num2str(negB),' || Left(Fourier): ',num2str(leftFouGain),' Right(Fourier): ',num2str(rightFouGain),' || Head Max(º/s):  ', num2str(peakH),' Eye Max: ',num2str(peakE));
if s~= 1
    resultPR = strcat('PR RESULTS: ',' Left PR Score: ',num2str(lPR),' Right PR score: ',num2str(rPR),' || Left/Right head peaks > 25º/s: ',num2str(lPeakN),'/',num2str(rPeakN),' || Left/Right velocity SD of head peaks: ',num2str(std(lHeadPeaks)),'/',num2str(std(rHeadPeaks)));
else
    resultPR = 'PR score is not available for VORS - supression - testing';
end
mTextBoxGain = uicontrol(figure1,'style','text');
mTextBoxPR = uicontrol(figure1,'style','text');
set(mTextBoxGain,'String',resultG);
set(mTextBoxGain,'FontSize',10);
set(mTextBoxGain,'HorizontalAlignment','left');
set(mTextBoxGain,'Position',[20 20 1300 25]);
set(mTextBoxPR,'String',resultPR);
set(mTextBoxPR,'FontSize',10);
set(mTextBoxPR,'HorizontalAlignment','left');
set(mTextBoxPR,'Position',[20 1 1600 25]);
set(figure1,'MenuBar','figure');
resultSNR = sprintf('Spectral Metrics || SPI Head: %.2f | Eye: %.2f  ||  SNR Head: %.1f dB | Eye: %.1f dB', ...
                     SPI_head, SPI_eye, SNR_head, SNR_eye);
mTextBoxSNR = uicontrol(figure1,'style','text');
set(mTextBoxSNR,'String',resultSNR);
set(mTextBoxSNR,'FontSize',10);
set(mTextBoxSNR,'HorizontalAlignment','left');
set(mTextBoxSNR,'Position',[20 42 1600 20]);
disp(resultG);
disp(resultPR);
% Console output for log/tracking
disp(['Spectral Periodicity Index (SPI) — Head: ', num2str(SPI_head), ...
      ' | Eye: ', num2str(SPI_eye)]);
disp(['Spectral SNR (dB) — Head: ', num2str(SNR_head), ...
      ' | Eye: ', num2str(SNR_eye)]);
end



