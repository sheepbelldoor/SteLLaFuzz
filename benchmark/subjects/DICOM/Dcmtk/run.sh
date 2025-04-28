#!/bin/bash

FUZZER=$1     #fuzzer name (e.g., aflnet) -- this name must match the name of the fuzzer folder inside the Docker container
OUTDIR=$2     #name of the output folder
OPTIONS=$3    #all configured options -- to make it flexible, we only fix some options (e.g., -i, -o, -N) in this script
TIMEOUT=$4    #time for fuzzing
SKIPCOUNT=$5  #used for calculating cov over time. e.g., SKIPCOUNT=5 means we run gcovr after every 5 test cases

strstr() {
  [ "${1#*$2*}" = "$1" ] && return 1
  return 0
}

#Commands for afl-based fuzzers (e.g., aflnet, aflnwe)
if $(strstr $FUZZER "afl") || $(strstr $FUZZER "llm") || $(strstr $FUZZER "snetgen"); then

  # Run fuzzer-specific commands (if any)
  if [ -e ${WORKDIR}/run-${FUZZER} ]; then
    source ${WORKDIR}/run-${FUZZER}
  fi

  TARGET_DIR=${TARGET_DIR:-"dcmtk"}
  INPUTS=${INPUTS:-${WORKDIR}"/in-dicom"}

  #Step-1. Do Fuzzing
  if [ $FUZZER = "chatafl-bin" ]; then
    pip install pydantic openai
    python3 enrich_corpus.py -o ${WORKDIR}/in-dicom -p DICOM
  fi
  if [ $FUZZER = "snetgen" ]; then
    pip install pydantic openai
    cd ${WORKDIR}
    python3 SNetGen.py -o ${WORKDIR}/in-dicom -p DICOM -s ${WORKDIR}/in-dicom
  fi
  #Move to fuzzing folder
  cd $WORKDIR/${TARGET_DIR}/build/bin
  if [ $FUZZER = "snetgen" ]; then
    # timeout -k 2s --preserve-status $TIMEOUT /home/ubuntu/${FUZZER}/afl-fuzz -d -i ${INPUTS} -o $OUTDIR -N tcp://127.0.0.1/5158 -x ${WORKDIR}/DICOM.dict $OPTIONS -c ${WORKDIR}/clean ./dcmqrscp --single-process
    timeout -k 2s --preserve-status $TIMEOUT /home/ubuntu/${FUZZER}/afl-fuzz -d -i ${INPUTS} -o $OUTDIR -N tcp://127.0.0.1/5158 $OPTIONS -c ${WORKDIR}/clean ./dcmqrscp --single-process
  else
    timeout -k 2s --preserve-status $TIMEOUT /home/ubuntu/${FUZZER}/afl-fuzz -d -i ${INPUTS} -o $OUTDIR -N tcp://127.0.0.1/5158 $OPTIONS -c ${WORKDIR}/clean ./dcmqrscp --single-process
  fi

  STATUS=$?

  #Step-2. Collect code coverage over time
  #Move to gcov folder
  cd $WORKDIR/dcmtk-gcov/build/bin

  #The last argument passed to cov_script should be 0 if the fuzzer is afl/nwe and it should be 1 if the fuzzer is based on aflnet
  #0: the test case is a concatenated message sequence -- there is no message boundary
  #1: the test case is a structured file keeping several request messages
  if [ $FUZZER = "aflnwe" ]; then
    cov_script ${WORKDIR}/${TARGET_DIR}/build/bin/${OUTDIR}/ 5158 ${SKIPCOUNT} ${WORKDIR}/${TARGET_DIR}/build/bin/${OUTDIR}/cov_over_time.csv 0
  else
    cov_script ${WORKDIR}/${TARGET_DIR}/build/bin/${OUTDIR}/ 5158 ${SKIPCOUNT} ${WORKDIR}/${TARGET_DIR}/build/bin/${OUTDIR}/cov_over_time.csv 1
  fi

  gcovr -r $WORKDIR/dcmtk-gcov --html --html-details -o index.html
  mkdir ${WORKDIR}/${TARGET_DIR}/build/bin/${OUTDIR}/cov_html/
  cp *.html ${WORKDIR}/${TARGET_DIR}/build/bin/${OUTDIR}/cov_html/

  if [ $FUZZER = "chatafl" ]; then
    cp -r ${WORKDIR}/answers ${WORKDIR}/${TARGET_DIR}/build/bin/${OUTDIR}/answers/
  fi

  if [ $FUZZER = "snetgen" ]; then
    cp -r ${WORKDIR}/in-dicom ${WORKDIR}/${TARGET_DIR}/build/bin/${OUTDIR}/in-dicom/
    cp -r ${WORKDIR}/llm_outputs ${WORKDIR}/${TARGET_DIR}/build/bin/${OUTDIR}/llm_outputs/
  fi

  #Step-3. Save the result to the ${WORKDIR} folder
  #Tar all results to a file
  cd ${WORKDIR}/${TARGET_DIR}/build/bin
  tar -zcvf ${WORKDIR}/${OUTDIR}.tar.gz ${OUTDIR}

  exit $STATUS
fi
